"""The DAG's run week comes from the end of the run's data interval. Needs Airflow, so it runs inside
the airflow container (docker compose exec airflow python -m pytest /opt/project/tests/test_dag.py);
elsewhere it is skipped."""

import sys
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("airflow")
from airflow.timetables.base import TimeRestriction  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent.parent / "dags"))
import egypt_prices  # noqa: E402

DAG = egypt_prices.dag


def run_week(**context):
    """The run week every task gets, rendered from the task's own argument."""
    template = DAG.get_task("load_silver").op_args[0]
    return egypt_prices.run_week(DAG.get_template_env().from_string(template).render(**context))


def test_a_scheduled_run_firing_on_2026_10_11_reads_week_2026_10_11():
    first = DAG.timetable.next_dagrun_info(
        last_automated_data_interval=None,
        restriction=TimeRestriction(earliest=DAG.start_date, latest=None, catchup=True))
    assert first.run_after == datetime(2026, 10, 11, tzinfo=timezone.utc)
    assert run_week(data_interval_end=first.data_interval.end) == date(2026, 10, 11)


def test_a_manual_run_inside_week_2026_10_04_reads_week_2026_10_04():
    interval = DAG.timetable.infer_manual_data_interval(run_after=datetime(2026, 10, 5, 2, 50, tzinfo=timezone.utc))
    assert run_week(data_interval_end=interval.end) == date(2026, 10, 4)


def test_a_manual_run_with_no_data_interval_reads_the_week_of_its_run_after():
    # An API trigger with "logical_date": null gives no data_interval_end in the context.
    dag_run = SimpleNamespace(run_after=datetime(2026, 10, 7, 9, 0, tzinfo=timezone.utc))
    assert run_week(dag_run=dag_run) == date(2026, 10, 4)
