from datetime import datetime, time, tzinfo, timezone, timedelta
from repositories.audit_repository import AuditRepository

class StatsService:
    def __init__(self, audit_repository: AuditRepository):
        self.audit_repository = audit_repository

    async def get_today_stats(self) -> dict:
        tz = timezone(timedelta(hours=-3))
        now = datetime.now(tz)
        
        start_date = datetime.combine(now.date(), time.min).replace(tzinfo=tz)
        end_date = datetime.combine(now.date(), time.max).replace(tzinfo=tz)

        stats_list = await self.audit_repository.get_daily_stats(start_date, end_date)
        
        if not stats_list:
            return {
                "dia": start_date.strftime("%Y-%m-%d"),
                "jogadas_concedidas": 0,
                "jogadas_consumidas": 0
            }
        
        # In this context we are usually querying a single day, or the last item in the list is today
        today_str = start_date.strftime("%Y-%m-%d")
        for stat in stats_list:
            if stat["dia"] == today_str:
                return stat
                
        return stats_list[-1]
