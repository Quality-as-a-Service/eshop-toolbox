import os
import logging
import hashlib
from collections import defaultdict

from azure.data.tables import TableServiceClient
from azure.core.credentials import AzureNamedKeyCredential
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.eventgrid import EventGridPublisherClient, EventGridEvent

from parsers.bazos import (
    list_offers as bazos_list_offers,
    fetch_offer_by_url as bazos_offer_by_url,
)
from parsers.facebook import (
    list_offers as facebook_list_offers,
    fetch_offer_by_url as facebook_offer_by_url,
)
from parsers.sreality import (
    list_offers as sreality_list_offers,
    fetch_offer_by_url as sreality_offer_by_url,
)


KEY_VALUT_URL = os.environ["KEY_VALUT_URL"]
TABLE_STORAGE_KEY_SECRET_NAME = os.environ["TABLE_STORAGE_KEY_SECRET_NAME"]
TABLE_STORAGE_NAME = os.environ["TABLE_STORAGE_NAME"]
TABLE_STORAGE_OFFERS_TABLE_NAME = os.environ["TABLE_STORAGE_OFFERS_TABLE_NAME"]
EVENTGRID_TOPIC_ENDPOINT = os.environ["EVENTGRID_TOPIC_ENDPOINT"]

verbose_publish = os.environ.get("VERBOSE_PUBLISH") == "1"

# TODO: this should be configured per user
BAZOS_FILTER_QUERY = "?hledat=&rubriky=reality&hlokalita=76901&humkreis=40&cenaod=&cenado=&Submit=Hledat&order=&crp=&kitx=ano"
FACEBOOK_FILTER_QUERY = (
    "?sortBy=creation_time_descend&latitude=49.3336&longitude=17.5836&radius=40"
)
SREALITY_FILTER_QUERY = "?region=Hole%C5%A1ov&region-id=3125&region-typ=municipality&vzdalenost=25&stari=dnes"


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
        collection_failed = False

        rich_offers = defaultdict(list)

        for domain, domain_list, domain_fetch_by_url, filter_query in [
            ["bazos.cz", bazos_list_offers, bazos_offer_by_url, BAZOS_FILTER_QUERY],
            [
                "facebook.com",
                facebook_list_offers,
                None,
                FACEBOOK_FILTER_QUERY,
            ],
            [
                "sreality.cz",
                sreality_list_offers,
                sreality_offer_by_url,
                SREALITY_FILTER_QUERY,
            ],
        ]:
            logging.info(f"Parsing {domain}")

            offers = domain_list(filter_query)
            logging.info(f"Collected {len(offers)} offers")

            for offer in offers:
                detected = self._check_offer(domain=domain, uid=offer["url"])
                if not len(detected):
                    logging.info(f"New offer {offer['url']}")

                    try:
                        offer_meta = {
                            "author": None,
                            "title": None,
                            "description": None,
                        }
                        if domain_fetch_by_url is not None:
                            offer_meta = domain_fetch_by_url(offer["url"])
                    except Exception as e:
                        logging.info(f"Failed to collect offer {offer['url']}")
                        logging.exception(e)
                        collection_failed = True
                        continue

                    offer_meta.update(offer)
                    offer = offer_meta
                    rich_offers[domain].append(offer)

                    new_offer_detected = True
                    self._insert_offer(domain=domain, uid=offer["url"])

        return new_offer_detected, collection_failed, dict(**rich_offers)

    def report_new_offers(self, offers: dict[str, list[dict]]):
        offers_flat = []
        for collection in offers.values():
            offers_flat.extend(collection)
        offers_flat = [o["url"] for o in offers_flat]

        event = EventGridEvent(
            event_type="qaas.reality_market_watchdog.new_offer_detected",
            data={
                "verbose": verbose_publish,
                "offers_rich": offers,
                "offers_flat": offers_flat,
            },
            subject="reality_market",
            data_version="1.0",
        )

        self.eventgrid_client.send(event)


if __name__ == "__main__":
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.basicConfig(level=logging.INFO)
    manager = Manager()
    _, _, offers = manager.identify_new_offers()
    print(offers)
    # manager.report_new_offers(offers)  # Careful!
