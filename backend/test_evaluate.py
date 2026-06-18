import sys
import os
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.daily_jobs import evaluate_dynamic_rules

print("Running evaluate_dynamic_rules to test email sending...")
try:
    evaluate_dynamic_rules()
    print("Finished evaluating dynamic rules.")
except Exception as e:
    traceback.print_exc()
