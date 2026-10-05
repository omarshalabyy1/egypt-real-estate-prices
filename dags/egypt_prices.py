"""Egyptian residential asking prices, once a week, in three layers:

- Bronze: one extract_<site> per automated site in config/client.yaml (the demo: realestate,
  propertyfinder, dubizzle and nawy) reads its site in parallel, each at its own pace, and keep every page under data/raw/<source>/<run_week>/
  (the JSON sites keep only the page's JSON, contact fields removed). Each fails on its own when
  page 1 of an area gives no priced row. A week already extracted (a _done file) is skipped.
- Silver: load_silver parses every site's pages for the week, checks each row, quarantines the
  failures and logs reconciled counts per site and area, in one transaction.
- Gold: build_gold rebuilds the star for the week; report prints the week's cuts and widest gaps.

Bayut and Aqarmap refuse plain HTTP readers, so they are a manual step BEFORE the weekly run: Omar
runs fetch_bayut_aqarmap.py in a visible browser, which saves their pages under
data/raw/bayut/<run_week>/ and data/raw/aqarmap/<run_week>/; load_silver includes them when there.

Every task works on the run week of the end of the run's data interval (the Sunday on or before its
day in the schedule's time zone), never on today's date, so a rerun of a week stays that week. With the
demo's schedule (Sundays at midnight) a scheduled run firing on Sunday 2026-10-11 reads week
2026-10-11; a manual run triggered inside a week reads that week. The schedule and its time zone come
from config/client.yaml, read when Airflow parses this file.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pendulum
from airflow.sdk import dag, task
from airflow.timetables.interval import CronDataIntervalTimetable

import tracker
from config import load_config

schedule = load_config()["schedule"]
TZ = schedule["timezone"]

# The moment the run's data interval ends; a run triggered by API with a null logical date has no
# interval, so it falls back to the moment the run was asked for.
DAY = "{{ (data_interval_end if data_interval_end is defined else dag_run.run_after) | ts }}"


def run_week(day):
    return tracker.run_week_of(datetime.fromisoformat(day).astimezone(ZoneInfo(TZ)).date())


@dag(
    # A data-interval timetable, said explicitly: since Airflow 3 a plain cron schedule gives runs no interval.
    schedule=CronDataIntervalTimetable(schedule["cron"], timezone=TZ),
    start_date=pendulum.datetime(2026, 10, 4, tz=TZ),  # a Sunday; catchup is off, so only the latest week runs
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
)
def egypt_real_estate_prices():
    @task
    def extract(source, day):
        tracker.extract(source, run_week(day))

    @task
    def load_silver(day):
        tracker.load_silver(run_week(day))

    @task
    def build_gold(day):
        tracker.build_gold(run_week(day))

    @task
    def report(day):
        tracker.report(run_week(day))

    day = DAY
    extracts = [extract.override(task_id=f"extract_{source}")(source, day) for source in tracker.AUTOMATED]
    extracts >> load_silver(day) >> build_gold(day) >> report(day)


dag = egypt_real_estate_prices()
