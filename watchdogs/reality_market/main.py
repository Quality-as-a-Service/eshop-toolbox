import azure.functions as func

from reality_market.manager import Manager


def main(timer: func.TimerRequest) -> None:
    manager = Manager()
    if manager.identify_new_offers():
        manager.report_new_offers()
