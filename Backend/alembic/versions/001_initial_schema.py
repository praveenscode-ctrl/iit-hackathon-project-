# placeholder — initial schema migration
# all 17 tables will be created here
# table creation order:
#   1. users
#   2. otp_verifications
#   3. admin_profiles
#   4. refresh_tokens
#   5. classes
#   6. class_memberships
#   7. assignments
#   8. submissions
#   9. student_analytics
#  10. class_analytics
#  11. assignment_analytics
#  12. notifications
#  13. reminder_jobs
#  14. bulk_import_batches
#  15. bulk_import_errors
#  16. export_jobs
#  17. ai_query_logs
#  18. scheduler_jobs — managed by APScheduler, not created here

def upgrade():
    pass

def downgrade():
    pass
