"""Sleep quality scoring and personalized recommendation engine."""


def compute_sleep_score(metrics: dict) -> dict:
    """Compute a 0-100 sleep quality score from 5 sub-dimensions.

    Args:
        metrics: dict from src.metrics.compute_sleep_metrics()

    Returns:
        dict with total_score, grade, grade_label, subscores, flag
    """
    subscores = {}

    # --- Sub-score 1: Sleep Efficiency (max 25) ---
    se = metrics.get("睡眠效率 SE (%)", 0)
    if isinstance(se, str):
        se = 0
    if se >= 90:
        se_score = 25
    elif se >= 85:
        se_score = 22
    elif se >= 80:
        se_score = 18
    elif se >= 70:
        se_score = 12
    elif se >= 60:
        se_score = 6
    else:
        se_score = 2
    subscores["sleep_efficiency"] = {"score": se_score, "max": 25, "raw_value": round(float(se), 1)}

    # --- Sub-score 2: Total Sleep Time (max 25) ---
    tst = metrics.get("总睡眠时长 TST (分钟)", 0)
    if isinstance(tst, str):
        tst = 0
    if 420 <= tst <= 480:
        tst_score = 25
    elif 390 <= tst < 420:
        tst_score = 22
    elif 360 <= tst < 390:
        tst_score = 20
    elif 330 <= tst < 360:
        tst_score = 16
    elif 300 <= tst < 330:
        tst_score = 12
    elif tst < 300:
        tst_score = 6
    elif 480 < tst <= 540:
        tst_score = 18
    elif 540 < tst <= 600:
        tst_score = 12
    else:
        tst_score = 6
    subscores["total_sleep_time"] = {"score": tst_score, "max": 25, "raw_value": round(float(tst), 1)}

    # --- Sub-score 3: WASO (max 20) ---
    waso = metrics.get("入睡后清醒 WASO (分钟)", 0)
    if isinstance(waso, str):
        waso = 120
    if waso <= 15:
        waso_score = 20
    elif waso <= 30:
        waso_score = 18
    elif waso <= 60:
        waso_score = 14
    elif waso <= 90:
        waso_score = 10
    elif waso <= 120:
        waso_score = 6
    else:
        waso_score = 2
    subscores["waso"] = {"score": waso_score, "max": 20, "raw_value": round(float(waso), 1)}

    # --- Sub-score 4: Sleep Latency (max 15) ---
    latency = metrics.get("入睡潜伏期 (分钟)", 30)
    if isinstance(latency, str) or latency is None:
        latency = None
        latency_score = 0
        latency_max = 0
    else:
        latency = float(latency)
        if latency <= 10:
            latency_score = 15
        elif latency <= 20:
            latency_score = 14
        elif latency <= 30:
            latency_score = 12
        elif latency <= 45:
            latency_score = 8
        elif latency <= 60:
            latency_score = 5
        else:
            latency_score = 2
        latency_max = 15
    subscores["sleep_latency"] = {"score": latency_score, "max": latency_max, "raw_value": round(latency, 1) if latency else "N/A"}

    # --- Sub-score 5: REM Proportion (max 15) ---
    rem_pct = metrics.get("REM 占比 (%)", 20)
    if isinstance(rem_pct, str):
        rem_pct = 20
    if 20 <= rem_pct <= 25:
        rem_score = 15
    elif 18 <= rem_pct < 20:
        rem_score = 13
    elif 15 <= rem_pct < 18:
        rem_score = 11
    elif 25 < rem_pct <= 28:
        rem_score = 11
    elif rem_pct < 15:
        rem_score = 6
    else:
        rem_score = 8
    subscores["rem_proportion"] = {"score": rem_score, "max": 15, "raw_value": round(float(rem_pct), 1)}

    # --- Compute total ---
    actual_max = sum(s["max"] for s in subscores.values())
    actual_score = sum(s["score"] for s in subscores.values())
    if actual_max > 0:
        total_score = round(actual_score / actual_max * 100)
    else:
        total_score = 0
    total_score = max(0, min(100, total_score))

    # --- Grade ---
    if total_score >= 95:
        grade, grade_label = "A+", "极佳"
    elif total_score >= 85:
        grade, grade_label = "A", "优秀"
    elif total_score >= 75:
        grade, grade_label = "B+", "良好"
    elif total_score >= 65:
        grade, grade_label = "B", "不错"
    elif total_score >= 55:
        grade, grade_label = "C+", "一般"
    elif total_score >= 45:
        grade, grade_label = "C", "偏低"
    elif total_score >= 30:
        grade, grade_label = "D", "较差"
    else:
        grade, grade_label = "F", "严重不佳"

    # --- Primary flag ---
    flag = None
    lowest_key = min(subscores, key=lambda k: subscores[k]["score"] / max(1, subscores[k]["max"]))
    subscores_ratio = {k: s["score"] / max(1, s["max"]) for k, s in subscores.items()}
    if subscores_ratio[lowest_key] < 0.5:
        flag_names = {
            "sleep_efficiency": "睡眠效率偏低",
            "total_sleep_time": "睡眠时长不足",
            "waso": "夜间清醒时间过长",
            "sleep_latency": "入睡困难",
            "rem_proportion": "REM 比例异常",
        }
        flag = flag_names.get(lowest_key)

    return {
        "total_score": total_score,
        "grade": grade,
        "grade_label": grade_label,
        "subscores": {k: v for k, v in subscores.items()},
        "flag": flag,
    }


def generate_recommendations(metrics: dict, subscores: dict = None) -> list:
    """Generate personalized sleep recommendations based on metrics.

    Returns:
        list of recommendation dicts with keys:
        priority, category, issue, advice, severity, reference
    """
    if subscores is None:
        score_data = compute_sleep_score(metrics)
        subscores = score_data.get("subscores", {})

    recommendations = []

    se = metrics.get("睡眠效率 SE (%)", 85)
    if isinstance(se, str):
        se = 0
    se = float(se)

    waso = metrics.get("入睡后清醒 WASO (分钟)", 30)
    if isinstance(waso, str):
        waso = 120
    waso = float(waso)

    latency = metrics.get("入睡潜伏期 (分钟)", 15)
    if isinstance(latency, str) or latency is None:
        latency = 15
    latency = float(latency)

    tst = metrics.get("总睡眠时长 TST (分钟)", 420)
    if isinstance(tst, str):
        tst = 420
    tst = float(tst)

    rem_pct = metrics.get("REM 占比 (%)", 22)
    if isinstance(rem_pct, str):
        rem_pct = 22
    rem_pct = float(rem_pct)

    transitions = metrics.get("阶段转换次数", 30)
    if isinstance(transitions, str):
        transitions = 30
    transitions = int(transitions)

    # Rule 1: Low sleep efficiency
    if se < 85:
        severity = "critical" if se < 70 else "warning"
        priority = 1 if se < 75 else 2
        recommendations.append({
            "priority": priority,
            "category": "efficiency",
            "issue": f"睡眠效率为 {se:.0f}%，低于健康标准 85%",
            "advice": (
                "您的睡眠效率偏低，意味着在床上清醒的时间较多。建议："
                "① 只在感到困倦时上床；"
                "② 每天固定起床时间（包括周末）；"
                "③ 睡前 3 小时内避免饮酒；"
                "④ 如果躺下 20 分钟仍无法入睡，起床做些安静的活动，等困了再回床上。"
            ),
            "severity": severity,
            "reference": "AASM 临床实践指南",
        })

    # Rule 2: High WASO
    if waso > 60:
        recommendations.append({
            "priority": 1,
            "category": "fragmentation",
            "issue": f"入睡后清醒时间达 {waso:.0f} 分钟，睡眠碎片化明显",
            "advice": (
                "您在入睡后仍会长时间清醒，这可能与以下因素有关："
                "① 环境干扰（噪音、温度、光线）；"
                "② 压力或焦虑情绪；"
                "③ 生理因素。"
                "建议睡前进行 10 分钟渐进式肌肉放松练习，"
                "并保持睡眠日记以识别规律。若持续存在，建议咨询睡眠专科医生。"
            ),
            "severity": "warning",
            "reference": "Sleep Foundation",
        })

    # Rule 3: Long sleep latency
    if latency > 30:
        recommendations.append({
            "priority": 1,
            "category": "latency",
            "issue": f"入睡耗时 {latency:.0f} 分钟，超过 30 分钟正常上限",
            "advice": (
                "入睡困难可能由多种因素导致。建议："
                "① 建立固定的睡前习惯（阅读、冥想、温水澡）；"
                "② 睡前 60 分钟停止使用电子屏幕；"
                "③ 下午 2 点后避免摄入咖啡因；"
                "④ 保持卧室凉爽（18°C 左右）；"
                "⑤ 白天进行适量运动，但睡前 3 小时避免剧烈运动。"
            ),
            "severity": "warning",
            "reference": "Sleep Foundation",
        })

    # Rule 4: Low REM
    if rem_pct < 15:
        recommendations.append({
            "priority": 2,
            "category": "rem",
            "issue": f"REM 占比仅 {rem_pct:.0f}%，低于正常 20-25% 范围",
            "advice": (
                "REM（快速眼动）睡眠对情绪调节和记忆巩固至关重要。REM 偏低常见原因："
                "① 饮酒（即使一杯也会抑制 REM）；"
                "② 某些药物（如抗抑郁药）；"
                "③ 作息不规律；"
                "④ 高度压力。"
                "建议记录饮酒与睡眠的关系，尽量保持固定的睡眠时间表。"
            ),
            "severity": "info",
            "reference": "NIH / NINDS",
        })

    # Rule 5: High REM (possible REM rebound)
    if rem_pct > 28:
        recommendations.append({
            "priority": 3,
            "category": "rem",
            "issue": f"REM 占比偏高 ({rem_pct:.0f}%)，可能提示 REM 反弹现象",
            "advice": (
                "REM 反弹通常发生在睡眠不足或 REM 被抑制后的恢复期。"
                "如果近期有补觉行为，这属于正常的生理调节。"
                "如果长期偏高，建议关注是否存在潜在的睡眠呼吸问题。"
            ),
            "severity": "info",
            "reference": "NIH / NINDS",
        })

    # Rule 6: Short sleep
    if tst < 360:
        recommendations.append({
            "priority": 2,
            "category": "duration",
            "issue": f"总睡眠时长仅 {tst:.0f} 分钟（{tst/60:.1f} 小时），不足 6 小时",
            "advice": (
                "长期睡眠不足会增加心血管疾病风险和认知功能下降风险。"
                "建议每晚提前 15 分钟上床，逐步延长睡眠时间。"
                "如果因工作或生活无法保证充足睡眠，"
                "周末适当补觉（但不要过度，以免打乱生物钟）。"
            ),
            "severity": "warning" if tst < 300 else "info",
            "reference": "AASM / CDC",
        })

    # Rule 7: Long sleep
    if tst > 540:
        recommendations.append({
            "priority": 3,
            "category": "duration",
            "issue": f"总睡眠时长 {tst:.0f} 分钟（{tst/60:.1f} 小时），超过 9 小时",
            "advice": (
                "长期睡眠超过 9 小时可能与睡眠质量不佳（碎片化睡眠导致长时间卧床）"
                "或潜在健康问题有关。如果伴有白天嗜睡，建议咨询医生。"
            ),
            "severity": "info",
            "reference": "Sleep Foundation",
        })

    # Rule 8: High transitions
    if transitions > 60:
        recommendations.append({
            "priority": 3,
            "category": "fragmentation",
            "issue": f"夜间阶段转换 {transitions} 次，睡眠不够稳定",
            "advice": (
                "睡眠阶段转换频繁意味着夜间多次醒来或处于浅睡状态。"
                "建议减少咖啡因摄入、优化卧室环境（遮光、隔音），"
                "以及评估是否存在睡眠呼吸暂停等睡眠障碍。"
            ),
            "severity": "info",
            "reference": "AASM",
        })

    # Rule 9: All good
    if not recommendations:
        recommendations.append({
            "priority": 3,
            "category": "general",
            "issue": "各项睡眠指标均在健康范围内",
            "advice": (
                "您的睡眠指标整体良好！请继续保持："
                "① 固定的作息时间；"
                "② 定期锻炼；"
                "③ 睡前放松习惯。"
                "良好的睡眠是健康的基石，继续保持！"
            ),
            "severity": "info",
            "reference": "AASM / CDC",
        })

    recommendations.sort(key=lambda r: r["priority"])
    return recommendations


def generate_reference_comparison(metrics: dict) -> dict:
    """Compare user metrics against healthy reference ranges.

    Returns:
        dict keyed by metric name with your_value, reference_range, status, interpretation
    """
    refs = {
        "总睡眠时长 TST (分钟)": {
            "reference_range": "360-480 分钟 (6-8 小时)",
            "normal_min": 360,
            "normal_max": 480,
            "borderline_min": 300,
            "borderline_max": 540,
            "interpretation_low": "睡眠时长偏短，建议争取更多睡眠时间",
            "interpretation_normal": "睡眠时长在健康范围内",
            "interpretation_high": "睡眠时长偏长，注意观察是否伴有白天嗜睡",
        },
        "睡眠效率 SE (%)": {
            "reference_range": ">85%",
            "normal_min": 85,
            "normal_max": 100,
            "borderline_min": 70,
            "borderline_max": 100,
            "interpretation_low": "睡眠效率偏低，床上清醒时间较多",
            "interpretation_normal": "睡眠效率良好",
            "interpretation_high": "",
        },
        "入睡后清醒 WASO (分钟)": {
            "reference_range": "<30 分钟",
            "normal_min": 0,
            "normal_max": 30,
            "borderline_min": 0,
            "borderline_max": 60,
            "interpretation_low": "",
            "interpretation_normal": "夜间清醒时间正常",
            "interpretation_high": "夜间清醒时间偏长，睡眠碎片化",
        },
        "入睡潜伏期 (分钟)": {
            "reference_range": "<30 分钟",
            "normal_min": 0,
            "normal_max": 30,
            "borderline_min": 0,
            "borderline_max": 45,
            "interpretation_low": "",
            "interpretation_normal": "入睡速度正常",
            "interpretation_high": "入睡较慢，可能存在入睡困难",
        },
        "NREM 占比 (%)": {
            "reference_range": "75-80% of TST",
            "normal_min": 70,
            "normal_max": 85,
            "borderline_min": 60,
            "borderline_max": 90,
            "interpretation_low": "NREM 占比偏低",
            "interpretation_normal": "NREM 占比正常",
            "interpretation_high": "NREM 占比偏高",
        },
        "REM 占比 (%)": {
            "reference_range": "20-25% of TST",
            "normal_min": 18,
            "normal_max": 28,
            "borderline_min": 15,
            "borderline_max": 30,
            "interpretation_low": "REM 占比偏低，可能影响记忆和情绪调节",
            "interpretation_normal": "REM 占比正常",
            "interpretation_high": "REM 占比偏高，可能提示 REM 反弹",
        },
        "阶段转换次数": {
            "reference_range": "20-40 次/晚",
            "normal_min": 15,
            "normal_max": 50,
            "borderline_min": 10,
            "borderline_max": 60,
            "interpretation_low": "阶段转换偏少，可能睡眠较深",
            "interpretation_normal": "阶段转换次数正常",
            "interpretation_high": "阶段转换偏多，睡眠较不稳定",
        },
    }

    result = {}
    for key, ref in refs.items():
        val = metrics.get(key)
        if val is None or isinstance(val, str):
            status = "unknown"
            interpretation = "数据不可用"
        else:
            val = float(val)
            if ref["normal_min"] <= val <= ref["normal_max"]:
                status = "normal"
                interpretation = ref["interpretation_normal"]
            elif val < ref["borderline_min"] or val > ref["borderline_max"]:
                status = "concerning"
                interpretation = ref["interpretation_low"] if val < ref["borderline_min"] else ref["interpretation_high"]
            else:
                status = "borderline"
                interpretation = ref["interpretation_low"] if val < ref["normal_min"] else ref["interpretation_high"]

        result[key] = {
            "your_value": val if isinstance(val, str) else round(float(val), 1),
            "reference_range": ref["reference_range"],
            "status": status,
            "interpretation": interpretation,
        }

    return result


def generate_summary_text(score_data: dict, recommendations: list) -> str:
    """Generate a plain-language, warm summary of the sleep analysis.

    Written at ~6th grade reading level, avoiding clinical jargon.
    """
    total = score_data.get("total_score", 0)
    grade = score_data.get("grade", "?")
    grade_label = score_data.get("grade_label", "未知")
    flag = score_data.get("flag")

    summaries = {
        (True, True): "您的睡眠质量整体不错！各项指标基本在健康范围内，请继续保持良好的睡眠习惯。",
        (True, False): "您的睡眠质量处于中等水平，有一些方面可以改善。认真看看下方的建议，做出小改变就能带来大不同。",
        (False, True): "您的睡眠质量不太理想，关键指标需要重点关注。别担心，下方提供了具体的改善建议，一步一步来就好。",
        (False, False): "您的睡眠质量需要引起重视，多项指标偏离了健康范围。建议认真阅读下方的个性化方案，并考虑咨询睡眠专科医生。",
    }

    good = total >= 70
    has_flag = flag is not None and len([r for r in recommendations if r["severity"] == "critical"]) == 0

    if total >= 85:
        template = summaries[(True, True)]
    elif total >= 70:
        template = summaries[(True, False)]
    elif total >= 50:
        template = summaries[(False, True)]
    else:
        template = summaries[(False, False)]

    if flag:
        template += f" 最值得关注的是：{flag}。"

    return {
        "score_summary": f"您的睡眠得分是 {total} 分（{grade}），属于「{grade_label}」水平。",
        "plain_summary": template,
        "headline": f"睡眠得分 {total} 分 · {grade_label}",
    }
