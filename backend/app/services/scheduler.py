from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.daily_jobs import evaluate_dynamic_rules
import logging

logger = logging.getLogger(__name__)

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run the daily evaluation at midnight every day
    trigger = CronTrigger(hour=0, minute=0)
    scheduler.add_job(evaluate_dynamic_rules, trigger=trigger, id='daily_dynamic_rules', replace_existing=True)
    
    scheduler.start()
    logger.info("Background scheduler started. Daily dynamic rules evaluation scheduled for midnight.")
    return scheduler
