from apscheduler.triggers.date import DateTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from apscheduler.triggers.interval import IntervalTrigger

from backend.models.job import ExecutionType, EventMapping
from backend.models.job import Job
from backend.tasks import job_tasks
from backend.helper import log

scheduler = BackgroundScheduler()
scheduler.start()
logger = log.setup_logging()


def create_job_schedule(job: Job, db):
    """
    Create a schedule for a job based on its execution type.

    Args:
        job (Job): The job to schedule.
        db: The database connection.

    Raises:
        Exception: If an invalid execution type is provided.
    """
    execution_type = db.query(ExecutionType).filter(
        ExecutionType.id == job.execution_type_id).first()

    event_mapping = db.query(EventMapping).filter(
        ExecutionType.id == job.event_mapping_id).first()

    if execution_type.name == "TIME_SPECIFIC":
        if job.recurring:
            execution_time = datetime.strptime(
                job.execution_time, "%Y-%m-%d %H:%M:%S")

            # Specify the time at which the job should run every day
            execution_time = time(
                hour=execution_time.hour, minute=execution_time.minute, second=execution_time.second)

            # Create an IntervalTrigger with a daily interval
            trigger = IntervalTrigger(days=1, start_date=execution_time)

            # Add the job with the recurring trigger
            job_scheduler_response = scheduler.add_job(
                job_tasks.execute_job, args=[
                    job.id], trigger=trigger, priority=job.priority
            )

            logger.info("Job has been scheduled: " +
                        str(job_scheduler_response))
            job_scheduler_response = job.job_scheduler_id = job_scheduler_response.id
        else:
            trigger = DateTrigger(
                run_date=job.execution_time)
            job_scheduler_response = scheduler.add_job(
                job_tasks.execute_job, args=[job.id], trigger=trigger, priority=job.priority)
            logger.info("Job has been scheduled: " +
                        str(job_scheduler_response))
            job.job_scheduler_id = job_scheduler_response.id

    elif execution_type.name == "EVENT_BASED":
        # Schedule the job to execute when the specified event occurs
        job_scheduler_response = scheduler.add_job(job_tasks.execute_job, args=[],
                                                   priority=job.priority, trigger='event', event_name=event_mapping.name)

        logger.info("Job has been scheduled: " + str(job_scheduler_response))

        job.job_scheduler_id = job_scheduler_response.id

    db.commit()


def stop_job_scheduler(job: Job, db):
    """
    Stop a scheduled job.

    Args:
        job (Job): The job to stop.
        db: The database connection.
    """
    try:
        # Step 3: Log the start of the operation
        logger.info(f"Stopping job scheduler for job ID: {job.id}")

        scheduler.remove_job(job.job_scheduler_id)

        job.status = "Cancelled"
        job.updated_at = datetime.now()
        db.commit()

        logger.info("Job scheduler stopped successfully")
    except Exception as e:
        # Step 4: Log the error if an exception occurs
        logger.exception(
            f"An error occurred while stopping job scheduler: {str(e)}")
