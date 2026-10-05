"""Egyptian residential asking prices, once a week: load the reference data, read the asking price
of every residential unit on realestate.eg's index pages for our six areas, and print this week's
competitor price cuts and our units' gap to the market.

Each run reads today's asking prices: the site only shows the current price, so a run never uses
its data interval and there is nothing to catch up on. The first run is the baseline; from the
second run on, price_change shows each cut and rise between two runs.
"""

from datetime import date, datetime, timedelta, timezone

from airflow.sdk import dag, task
from airflow.timetables.interval import DeltaDataIntervalTimetable

import tracker


@dag(
    # Said explicitly: since Airflow 3 a plain timedelta schedule gives runs no interval.
    schedule=DeltaDataIntervalTimetable(timedelta(weeks=1)),
    start_date=datetime(2026, 10, 4, tzinfo=timezone.utc),  # a Sunday
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
)
def egypt_real_estate_prices():
    @task
    def load_reference():
        tracker.load_reference()

    @task
    def collect():
        run_week = tracker.this_week()
        tracker.collect(run_week)
        return run_week.isoformat()  # report prints the same week, even if the run crosses midnight

    @task
    def report(run_week):
        tracker.report(date.fromisoformat(run_week))

    run_week = collect()
    load_reference() >> run_week
    report(run_week)


egypt_real_estate_prices()
