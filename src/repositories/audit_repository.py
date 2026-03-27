from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase


class AuditRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.audit_events

    async def create(self, event: str, payload: dict) -> None:
        await self.collection.insert_one(
            {"event": event, "payload": payload, "created_at": datetime.now(timezone.utc)}
        )

    async def get_daily_stats(self, start_date: datetime, end_date: datetime) -> list[dict]:
        # Generating list of dates in YYYY-MM-DD format between start_date and end_date
        import pandas as pd
        date_range = pd.date_range(start_date, end_date - pd.Timedelta(days=1), freq='D').strftime('%Y-%m-%d').tolist()
        if not date_range:
            date_range = [start_date.strftime('%Y-%m-%d')]

        pipeline = [
            {
                "$facet": {
                    "notas": [
                        {
                            "$match": {
                                "event": "session-created",
                                "created_at": {"$gte": start_date, "$lt": end_date}
                            }
                        },
                        {
                            "$project": {
                                "dia": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                                "qtd_notas": {"$size": {"$ifNull": ["$payload.receipt_ids", []]}}
                            }
                        },
                        {
                            "$group": {
                                "_id": "$dia",
                                "notas": {"$sum": "$qtd_notas"}
                            }
                        }
                    ],
                    "concedidas": [
                        {
                            "$match": {
                                "event": "session-created",
                                "created_at": {"$gte": start_date, "$lt": end_date}
                            }
                        },
                        {
                            "$project": {
                                "dia": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                                "total_plays": "$payload.total_plays"
                            }
                        },
                        {
                            "$group": {
                                "_id": "$dia",
                                "jogadas_concedidas": {"$sum": "$total_plays"}
                            }
                        }
                    ],
                    "concedidas_ponderadas_por_notas": [
                        {
                            "$match": {
                                "event": "session-created",
                                "created_at": {"$gte": start_date, "$lt": end_date}
                            }
                        },
                        {
                            "$project": {
                                "dia": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                                "qtd_notas": {"$size": {"$ifNull": ["$payload.receipt_ids", []]}},
                                "total_plays": {"$ifNull": ["$payload.total_plays", 0]}
                            }
                        },
                        {
                            "$project": {
                                "dia": 1,
                                "total_plays_ponderado": {"$multiply": ["$total_plays", "$qtd_notas"]}
                            }
                        },
                        {
                            "$group": {
                                "_id": "$dia",
                                "jogadas_concedidas_ponderadas_por_notas": {"$sum": "$total_plays_ponderado"}
                            }
                        }
                    ],
                    "consumidas": [
                        {
                            "$match": {
                                "event": {"$in": ["queue-play-consumed", "special-tag-used"]},
                                "created_at": {"$gte": start_date, "$lt": end_date}
                            }
                        },
                        {
                            "$project": {
                                "dia": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}
                            }
                        },
                        {
                            "$group": {
                                "_id": "$dia",
                                "jogadas_consumidas": {"$sum": 1}
                            }
                        }
                    ],
                    "canceladas": [
                        {
                            "$match": {
                                "event": "session-cancelled-for-reuse",
                                "created_at": {"$gte": start_date, "$lt": end_date}
                            }
                        },
                        {
                            "$project": {
                                "dia": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                                "tags_canceladas": {"$ifNull": ["$payload.invalidated_tags", 0]}
                            }
                        },
                        {
                            "$group": {
                                "_id": "$dia",
                                "jogadas_canceladas": {"$sum": "$tags_canceladas"}
                            }
                        }
                    ]
                }
            },
            {
                "$project": {
                    "combinado": {
                        "$map": {
                            "input": date_range,
                            "as": "dia",
                            "in": {
                                "dia": "$$dia",
                                "notas": {
                                    "$let": {
                                        "vars": {
                                            "item": {
                                                "$arrayElemAt": [
                                                    {
                                                        "$filter": {
                                                            "input": "$notas",
                                                            "as": "n",
                                                            "cond": {"$eq": ["$$n._id", "$$dia"]}
                                                        }
                                                    },
                                                    0
                                                ]
                                            }
                                        },
                                        "in": {"$ifNull": ["$$item.notas", 0]}
                                    }
                                },
                                "jogadas_concedidas": {
                                    "$let": {
                                        "vars": {
                                            "item": {
                                                "$arrayElemAt": [
                                                    {
                                                        "$filter": {
                                                            "input": "$concedidas",
                                                            "as": "c",
                                                            "cond": {"$eq": ["$$c._id", "$$dia"]}
                                                        }
                                                    },
                                                    0
                                                ]
                                            }
                                        },
                                        "in": {"$ifNull": ["$$item.jogadas_concedidas", 0]}
                                    }
                                },
                                "jogadas_concedidas_ponderadas_por_notas": {
                                    "$let": {
                                        "vars": {
                                            "item": {
                                                "$arrayElemAt": [
                                                    {
                                                        "$filter": {
                                                            "input": "$concedidas_ponderadas_por_notas",
                                                            "as": "p",
                                                            "cond": {"$eq": ["$$p._id", "$$dia"]}
                                                        }
                                                    },
                                                    0
                                                ]
                                            }
                                        },
                                        "in": {"$ifNull": ["$$item.jogadas_concedidas_ponderadas_por_notas", 0]}
                                    }
                                },
                                "jogadas_consumidas": {
                                    "$let": {
                                        "vars": {
                                            "item": {
                                                "$arrayElemAt": [
                                                    {
                                                        "$filter": {
                                                            "input": "$consumidas",
                                                            "as": "c",
                                                            "cond": {"$eq": ["$$c._id", "$$dia"]}
                                                        }
                                                    },
                                                    0
                                                ]
                                            }
                                        },
                                        "in": {"$ifNull": ["$$item.jogadas_consumidas", 0]}
                                    }
                                },
                                "jogadas_canceladas": {
                                    "$let": {
                                        "vars": {
                                            "item": {
                                                "$arrayElemAt": [
                                                    {
                                                        "$filter": {
                                                            "input": "$canceladas",
                                                            "as": "ca",
                                                            "cond": {"$eq": ["$$ca._id", "$$dia"]}
                                                        }
                                                    },
                                                    0
                                                ]
                                            }
                                        },
                                        "in": {"$ifNull": ["$$item.jogadas_canceladas", 0]}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            {"$unwind": "$combinado"},
            {
                "$project": {
                    "_id": 0,
                    "dia": "$combinado.dia",
                    "notas": "$combinado.notas",
                    "jogadas_consumidas": "$combinado.jogadas_consumidas",
                    "jogadas_concedidas": {
                        "$subtract": [
                            "$combinado.jogadas_concedidas",
                            "$combinado.jogadas_canceladas"
                        ]
                    },
                    "jogadas_concedidas_ponderadas_por_notas": {
                        "$subtract": [
                            "$combinado.jogadas_concedidas_ponderadas_por_notas",
                            "$combinado.jogadas_canceladas"
                        ]
                    },
                    "diferenca_concedidas_vs_consumidas": {
                        "$subtract": [
                            {"$subtract": ["$combinado.jogadas_concedidas", "$combinado.jogadas_canceladas"]},
                            "$combinado.jogadas_consumidas"
                        ]
                    },
                    "diferenca_ponderadas_vs_consumidas": {
                        "$subtract": [
                            {"$subtract": ["$combinado.jogadas_concedidas_ponderadas_por_notas", "$combinado.jogadas_canceladas"]},
                            "$combinado.jogadas_consumidas"
                        ]
                    }
                }
            },
            {"$sort": {"dia": 1}}
        ]

        cursor = self.collection.aggregate(pipeline)
        return await cursor.to_list(length=None)
