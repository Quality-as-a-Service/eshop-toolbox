import logging
import azure.functions as func

from manager import Manager

app = func.FunctionApp()


@app.function_name(name="realitymarket")
@app.timer_trigger(schedule="0 */15 * * * *", arg_name="timer", run_on_startup=True)
def main(timer: func.TimerRequest) -> None:
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.basicConfig(level=logging.INFO)
    manager = Manager()
    new_offer_detected, collection_failed, offers = manager.identify_new_offers()
    if new_offer_detected:
        manager.report_new_offers(offers)
    if collection_failed:
        raise RuntimeError("Collection failed")
