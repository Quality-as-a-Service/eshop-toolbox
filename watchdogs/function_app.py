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
    new_offers, sources = manager.identify_new_offers()
    if new_offers:
        manager.report_new_offers(sources)