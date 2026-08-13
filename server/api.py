from fastapi import APIRouter, Request
from pydantic import BaseModel
from datetime import datetime, timezone
import json

from auth import get_current_user
from models import get_progress, save_progress

router = APIRouter(prefix="/api", tags=["progress"])


class ProgressData(BaseModel):
    data: dict


def _parse_json(val, default):
    """把字符串/字典安全地解析为对象，失败返回默认值"""
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (ValueError, TypeError):
            return default
    if isinstance(val, (dict, list)):
        return val
    return default


def merge_progress(existing: dict, incoming: dict) -> dict:
    """字段级合并：词统计取并集、时长累加、进度取较新，不丢任何设备数据"""
    merged = {k: v for k, v in existing.items() if k != '_updated_at'}

    # 1. 词统计：按词取并集；同一词取 lastReviewDate 较新者
    if 'wenyan_word_stats' in incoming:
        e_stats = _parse_json(existing.get('wenyan_word_stats'), {})
        i_stats = _parse_json(incoming.get('wenyan_word_stats'), {})
        for word, stat in i_stats.items():
            if word not in e_stats:
                e_stats[word] = stat
            else:
                e_date = str(e_stats[word].get('lastReviewDate', '') or '') \
                    if isinstance(e_stats[word], dict) else ''
                i_date = str(stat.get('lastReviewDate', '') or '') \
                    if isinstance(stat, dict) else ''
                if i_date > e_date:
                    e_stats[word] = stat
        merged['wenyan_word_stats'] = json.dumps(e_stats, ensure_ascii=False)

    # 2. 每日活动：learn/review 取并集，时长用增量累加
    e_act = _parse_json(existing.get('wenyan_daily_activity'), {})
    i_act = _parse_json(incoming.get('wenyan_daily_activity'), {})
    try:
        delta = int(incoming.get('seconds_delta', 0) or 0)
    except (ValueError, TypeError):
        delta = 0

    e_date = str(e_act.get('date', '') or '')
    i_date = str(i_act.get('date', '') or '')

    if i_date == e_date and i_date:
        learn = list(dict.fromkeys(e_act.get('learn', []) + i_act.get('learn', [])))
        review = list(dict.fromkeys(e_act.get('review', []) + i_act.get('review', [])))
        seconds = int(e_act.get('seconds', 0) or 0) + delta
        merged_act = {'date': i_date, 'learn': learn, 'review': review, 'seconds': seconds}
    elif i_date > e_date:
        # 新的一天，以 incoming 为准
        merged_act = {
            'date': i_date,
            'learn': list(i_act.get('learn', [])),
            'review': list(i_act.get('review', [])),
            'seconds': delta,
        }
    else:
        # incoming 日期为空或更旧，保持现有
        merged_act = e_act

    merged['wenyan_daily_activity'] = json.dumps(merged_act, ensure_ascii=False)

    # 3. 进度整数取较大值
    for key in ['wenyan_mc_group', 'wenyan_mem_idx', 'wenyan_mc_review_group']:
        if key in incoming:
            try:
                e_val = int(existing.get(key, 0) or 0)
                i_val = int(incoming[key] or 0)
                merged[key] = str(max(e_val, i_val))
            except (ValueError, TypeError):
                merged[key] = incoming[key]

    # 4. 最后学习日期取较新
    if 'wenyan_last_date' in incoming:
        merged['wenyan_last_date'] = max(
            str(existing.get('wenyan_last_date', '') or ''),
            str(incoming.get('wenyan_last_date', '') or ''),
        )

    return merged


@router.get("/progress")
def api_get_progress(request: Request):
    user = get_current_user(request)
    data = get_progress(user["user_id"])
    return {"ok": True, "data": data, "updated_at": data.get("_updated_at", "")}


@router.post("/progress")
def api_save_progress(request: Request, body: ProgressData):
    user = get_current_user(request)
    existing = get_progress(user["user_id"])
    merged = merge_progress(existing, body.data)
    merged["_updated_at"] = datetime.now(timezone.utc).isoformat()
    save_progress(user["user_id"], merged)
    return {"ok": True, "data": merged}
