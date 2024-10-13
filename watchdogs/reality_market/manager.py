import os
import logging
import hashlib

from azure.data.tables import TableServiceClient
from azure.core.credentials import AzureNamedKeyCredential
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.eventgrid import EventGridPublisherClient, EventGridEvent

from reality_market.parsers.bazos import fetch_single_page as bazos_fetch
from reality_market.parsers.facebook import fetch_single_page as facebook_fetch
from reality_market.parsers.sreality import fetch_single_page as sreality_fetch


KEY_VALUT_URL = os.environ["KEY_VALUT_URL"]
TABLE_STORAGE_KEY_SECRET_NAME = os.environ["TABLE_STORAGE_KEY_SECRET_NAME"]
TABLE_STORAGE_NAME = os.environ["TABLE_STORAGE_NAME"]
TABLE_STORAGE_OFFERS_TABLE_NAME = os.environ["TABLE_STORAGE_OFFERS_TABLE_NAME"]
EVENTGRID_TOPIC_ENDPOINT = os.environ["EVENTGRID_TOPIC_ENDPOINT"]

verbose_publish = (
    os.environ.get("FUNCTIONS_EXTENSION_VERSION") is not None
    and os.environ.get("FUNCTIONS_WORKER_RUNTIME") is not None
)

BAZOS_FILTER_QUERY = "/?hledat=&rubriky=reality&hlokalita=76001&humkreis=10&cenaod=&cenado=&order=&crp=&kitx=ano"
FACEBOOK_FILTER_QUERY = "/?latitude=49.2239&longitude=17.6688&radius=88"
SREALITY_FILTER_QUERY = (
    "?category_main_cb=1&category_type_cb=1&locality_region_id=9&per_page=20"
)


class Manager:
    def __init__(self):
        default_az_credential = DefaultAzureCredential()
        secret_client = SecretClient(
            vault_url=KEY_VALUT_URL, credential=default_az_credential
        )
        table_storage_key = secret_client.get_secret(TABLE_STORAGE_KEY_SECRET_NAME)
        table_service_client = TableServiceClient(
            endpoint=f"https://{TABLE_STORAGE_NAME}.table.core.windows.net",
            credential=AzureNamedKeyCredential(
                TABLE_STORAGE_NAME, table_storage_key.value
            ),
        )
        self.table_client = table_service_client.get_table_client(
            TABLE_STORAGE_OFFERS_TABLE_NAME
        )
        self.eventgrid_client = EventGridPublisherClient(
            EVENTGRID_TOPIC_ENDPOINT, default_az_credential
        )

    def _insert_offer(self, domain: str, uid: str):
        self.table_client.create_entity(
            entity={
                "PartitionKey": domain,
                "RowKey": hashlib.sha256(uid.encode()).hexdigest(),
            }
        )
        pass

    def _check_offer(self, domain: str, uid: str):
        return list(
            self.table_client.query_entities(
                query_filter="PartitionKey eq @domain and RowKey eq @uid",
                parameters={
                    "domain": domain,
                    "uid": hashlib.sha256(uid.encode()).hexdigest(),
                },
            )
        )

    def identify_new_offers(self):
        new_offer_detected = False

        for domain, fetch, filter_query in [
            ["bazos.cz", bazos_fetch, BAZOS_FILTER_QUERY],
            ["facebook.com", facebook_fetch, FACEBOOK_FILTER_QUERY],
            ["sreality.cz", sreality_fetch, SREALITY_FILTER_QUERY],
        ]:
            logging.info(f"Parsing {domain}")
            items = fetch(filter_query)
            logging.info(f"Collected {len(items)} items")
            for item in items:
                detected = self._check_offer(domain=domain, uid=item)
                if not len(detected):
                    new_offer_detected = True
                    self._insert_offer(domain=domain, uid=item)

        return new_offer_detected

    def report_new_offers(self):
        event = EventGridEvent(
            event_type="qaas.reality_market_watchdog.new_offer_detected",
            data={"verbose": verbose_publish},
            subject="reality_market",
            data_version="1.0",
        )

        self.eventgrid_client.send(event)


if __name__ == "__main__":
    manager = Manager()
    # manager.identify_new_offers()
    manager.report_new_offers()
