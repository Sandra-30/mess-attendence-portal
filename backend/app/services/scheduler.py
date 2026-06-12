from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.daily_jobs import evaluate_dynamic_rules, generate_monthly_summary
import logging

logger = logging.getLogger(__name__)

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run the daily evaluation at midnight every day
    trigger = CronTrigger(hour=0, minute=0)
    scheduler.add_job(evaluate_dynamic_rules, trigger=trigger, id='daily_dynamic_rules', replace_existing=True)
    
    # Run the monthly summary on the 1st of every month at 00:05
    monthly_trigger = CronTrigger(day=1, hour=0, minute=5)
    scheduler.add_job(generate_monthly_summary, trigger=monthly_trigger, id='monthly_summary_notif', replace_existing=True)
    
    scheduler.start()
    logger.info("Background scheduler started. Daily dynamic rules evaluation scheduled for midnight.")
    return scheduler
