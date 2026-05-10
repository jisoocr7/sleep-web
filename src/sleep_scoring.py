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
            "rem_proportion": "做梦比例异常",
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

    Rule engine with:
    - Refined single-metric boundaries (mild / moderate / severe)
    - Combination rules (multi-metric patterns)
    - Max 4 recommendations to avoid information overload

    Returns:
        list of recommendation dicts with keys:
        priority, category, issue, advice, severity, reference
    """
    if subscores is None:
        score_data = compute_sleep_score(metrics)
        subscores = score_data.get("subscores", {})

    # --- Parse metrics ---
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

    recommendations = []
    # Track which single-metric categories are covered by combo rules
    covered_categories = set()

    # =============================================================
    # Phase 1: Combination rules (higher priority, more specific)
    # =============================================================

    # Combo 1: Insomnia pattern — low efficiency + long latency
    if se < 80 and latency > 30:
        covered_categories.update(["efficiency", "latency"])
        recommendations.append({
            "priority": 1,
            "category": "insomnia_pattern",
            "issue": f"入睡困难（{latency:.0f} 分钟）且睡眠效率低（{se:.0f}%），符合失眠特征",
            "advice": (
                "入睡慢加上床上清醒时间多，是典型的失眠表现。"
                "医学上推荐「CBT-I」（认知行为疗法）作为一线干预，核心方法："
                "① 固定时间起床（包括周末），不补觉；"
                "② 只在困了才上床，躺 20 分钟睡不着就起来；"
                "③ 减少卧床时间，让睡眠更集中；"
                "④ 睡前 1 小时停止看屏幕。"
                "如果持续 2 周以上，建议咨询睡眠专科医生。"
            ),
            "severity": "critical",
            "reference": "AASM CBT-I 临床指南",
        })

    # Combo 2: Fragmented sleep — high WASO + frequent transitions
    if waso > 60 and transitions > 60:
        covered_categories.update(["fragmentation"])
        severity_frag = "critical" if waso > 90 else "warning"
        recommendations.append({
            "priority": 1,
            "category": "fragmentation_combo",
            "issue": f"中途清醒 {waso:.0f} 分钟且阶段转换 {transitions} 次，睡眠严重碎片化",
            "advice": (
                "频繁醒来加上大量阶段转换，说明整晚睡眠不断被打断。"
                "常见原因：① 睡眠呼吸暂停（打鼾、憋气）；"
                "② 不宁腿综合征（腿部不适、想动）；"
                "③ 环境干扰（噪音、光线、温度）；"
                "④ 夜间频繁起夜。"
                "建议先排查环境因素，如果打鼾或有憋醒现象，建议做睡眠监测排除呼吸暂停。"
            ),
            "severity": severity_frag,
            "reference": "AASM",
        })

    # Combo 3: Sleep restriction — short sleep but high efficiency
    if tst < 360 and se >= 85:
        covered_categories.update(["duration"])
        recommendations.append({
            "priority": 2,
            "category": "sleep_restriction",
            "issue": f"总睡眠仅 {tst/60:.1f} 小时，但睡眠效率 {se:.0f}%，说明睡得少但睡得好",
            "advice": (
                "你的睡眠效率很高，说明身体具备良好的睡眠能力，只是卧床时间不够。"
                "可能是主动减少了睡眠（加班、熬夜），也可能是上床太晚。"
                "建议：① 每周提前 15 分钟上床，逐步延长到 7-8 小时；"
                "② 睡眠效率高是好事，保持这个质量，把时间加上去就完美了。"
            ),
            "severity": "info",
            "reference": "AASM / CDC",
        })

    # Combo 4: Long time in bed but poor efficiency
    if se < 80 and tst > 480:
        covered_categories.update(["efficiency", "duration"])
        recommendations.append({
            "priority": 2,
            "category": "long_bed",
            "issue": f"卧床时间较长但睡眠效率仅 {se:.0f}%，清醒时间占比高",
            "advice": (
                "你躺在床上的时间很长，但实际睡眠占比不高。"
                "这在医学上叫「卧床时间过长」，会让大脑把床和清醒联系起来，反而更难入睡。"
                "建议尝试「睡眠限制疗法」：先把卧床时间缩短到实际睡眠时间，"
                "等效率提升后再逐步延长。比如实际睡了 6 小时，就只在床上待 6.5 小时。"
            ),
            "severity": "warning",
            "reference": "AASM CBT-I 临床指南",
        })

    # Combo 5: Recovery sleep — short sleep + high REM
    if tst < 360 and rem_pct > 28:
        covered_categories.update(["duration", "rem"])
        recommendations.append({
            "priority": 2,
            "category": "recovery_sleep",
            "issue": f"总睡眠仅 {tst/60:.1f} 小时但做梦期占比 {rem_pct:.0f}%，身体在优先补回 REM",
            "advice": (
                "睡眠不足时，身体会在补觉阶段优先补回做梦期（REM），"
                "这叫「REM 反弹」，是正常的自我修复机制。"
                "说明你之前可能欠了觉或 REM 被压制（如饮酒后）。"
                "短期出现属于正常，但要避免反复欠觉——长期睡眠不足会增加心血管疾病和认知下降风险。"
                "建议：逐步把睡眠时间延长到 7 小时以上。"
            ),
            "severity": "warning",
            "reference": "Sleep Foundation / NIH",
        })

    # Combo 6: Alcohol effect — low REM + high WASO
    if rem_pct < 15 and waso > 60:
        covered_categories.update(["rem", "fragmentation"])
        recommendations.append({
            "priority": 2,
            "category": "alcohol_effect",
            "issue": f"做梦期仅 {rem_pct:.0f}% 且中途清醒 {waso:.0f} 分钟，可能与饮酒有关",
            "advice": (
                "做梦期被压制加上频繁醒来，是饮酒后常见的睡眠模式。"
                "酒精会抑制 REM 睡眠并导致后半夜觉醒增多。"
                "即使少量饮酒（一两杯红酒）也会明显影响睡眠结构。"
                "建议：① 睡前 3-4 小时避免饮酒；"
                "② 观察不饮酒的夜晚睡眠是否改善；"
                "③ 如果不饮酒时仍持续如此，建议咨询医生排查其他原因。"
            ),
            "severity": "warning",
            "reference": "Sleep Foundation / AASM",
        })

    # =============================================================
    # Phase 2: Single-metric rules (only if not covered by combos)
    # =============================================================

    # Sleep efficiency
    if se < 85 and "efficiency" not in covered_categories:
        if se < 70:
            severity, priority = "critical", 1
        elif se < 75:
            severity, priority = "warning", 1
        elif se < 80:
            severity, priority = "warning", 2
        else:
            severity, priority = "info", 3
        recommendations.append({
            "priority": priority,
            "category": "efficiency",
            "issue": f"睡眠效率为 {se:.0f}%，{'明显' if se < 75 else '略'}低于健康标准 85%",
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

    # WASO
    if waso > 30 and "fragmentation" not in covered_categories:
        if waso > 90:
            severity, priority = "critical", 1
        elif waso > 60:
            severity, priority = "warning", 1
        else:
            severity, priority = "info", 3
        recommendations.append({
            "priority": priority,
            "category": "fragmentation",
            "issue": f"入睡后清醒时间达 {waso:.0f} 分钟，{'明显' if waso > 60 else '略微'}偏高",
            "advice": (
                "您在入睡后仍会长时间清醒，这可能与以下因素有关："
                "① 环境干扰（噪音、温度、光线）；"
                "② 压力或焦虑情绪；"
                "③ 生理因素。"
                "建议睡前进行 10 分钟渐进式肌肉放松练习，"
                "并保持睡眠日记以识别规律。若持续存在，建议咨询睡眠专科医生。"
            ),
            "severity": severity,
            "reference": "Sleep Foundation",
        })

    # Sleep latency
    if latency > 20 and "latency" not in covered_categories:
        if latency > 45:
            severity, priority = "critical", 1
        elif latency > 30:
            severity, priority = "warning", 1
        else:
            severity, priority = "info", 3
        recommendations.append({
            "priority": priority,
            "category": "latency",
            "issue": f"入睡耗时 {latency:.0f} 分钟，{'超过' if latency > 30 else '接近'}30 分钟正常上限",
            "advice": (
                "入睡困难可能由多种因素导致。建议："
                "① 建立固定的睡前习惯（阅读、冥想、温水澡）；"
                "② 睡前 60 分钟停止使用电子屏幕；"
                "③ 下午 2 点后避免摄入咖啡因；"
                "④ 保持卧室凉爽（18°C 左右）；"
                "⑤ 白天进行适量运动，但睡前 3 小时避免剧烈运动。"
            ),
            "severity": severity,
            "reference": "Sleep Foundation",
        })

    # Low REM
    if rem_pct < 15 and "rem" not in covered_categories:
        recommendations.append({
            "priority": 2,
            "category": "rem",
            "issue": f"做梦期占比仅 {rem_pct:.0f}%，低于正常 20-25% 范围",
            "advice": (
                "做梦期（REM 睡眠）对情绪调节和记忆巩固至关重要，就像大脑在夜间「整理文件」。偏少常见原因："
                "① 饮酒（即使一杯也会抑制做梦）；"
                "② 某些药物（如抗抑郁药）；"
                "③ 作息不规律；"
                "④ 高度压力。"
                "建议记录饮酒与睡眠的关系，尽量保持固定的睡眠时间表。"
            ),
            "severity": "info",
            "reference": "NIH / NINDS",
        })

    # High REM
    if rem_pct > 28 and "rem" not in covered_categories:
        recommendations.append({
            "priority": 3,
            "category": "rem",
            "issue": f"做梦期占比偏高 ({rem_pct:.0f}%)，可能是身体在「补觉」",
            "advice": (
                "做梦期偏高在医学上称为「REM 反弹」——身体在补偿之前被压制的做梦时间。"
                "常见原因：① 近期睡眠不足，补觉时优先补回 REM；"
                "② 戒酒或停用某些药物（如抗抑郁药、安眠药）；"
                "③ 近期经历了较大压力，大脑通过增加 REM 来调节情绪。"
                "REM 反弹是身体的自我修复机制，短期出现属于正常。"
                "如果持续偏高，建议保持规律作息、减少饮酒，必要时咨询医生。"
            ),
            "severity": "info",
            "reference": "NIH / NINDS",
        })

    # Short sleep
    if tst < 360 and "duration" not in covered_categories:
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

    # Long sleep
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

    # High transitions (only if not already covered by fragmentation_combo)
    if transitions > 50 and "fragmentation" not in covered_categories:
        if transitions > 60:
            severity, priority = "info", 3
        else:
            severity, priority = "info", 3
        recommendations.append({
            "priority": priority,
            "category": "fragmentation",
            "issue": f"夜间阶段转换 {transitions} 次，睡眠不够稳定",
            "advice": (
                "睡眠阶段转换频繁意味着夜间多次醒来或处于浅睡状态。"
                "建议减少咖啡因摄入、优化卧室环境（遮光、隔音），"
                "以及评估是否存在睡眠呼吸暂停等睡眠障碍。"
            ),
            "severity": severity,
            "reference": "AASM",
        })

    # =============================================================
    # Phase 3: All good
    # =============================================================
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

    # Sort by priority and cap at 4
    recommendations.sort(key=lambda r: r["priority"])
    return recommendations[:4]


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
            "interpretation_low": "深睡眠比例偏低",
            "interpretation_normal": "深睡眠比例正常",
            "interpretation_high": "深睡眠比例偏高",
        },
        "REM 占比 (%)": {
            "reference_range": "20-25% of TST",
            "normal_min": 18,
            "normal_max": 28,
            "borderline_min": 15,
            "borderline_max": 30,
            "interpretation_low": "做梦比例偏低，可能影响记忆和情绪调节",
            "interpretation_normal": "做梦比例正常",
            "interpretation_high": "做梦比例偏高，可能是身体在补觉",
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
    """Generate a plain-language, warm summary of the sleep analysis."""
    total = score_data.get("total_score", 0)
    grade = score_data.get("grade", "?")
    grade_label = score_data.get("grade_label", "未知")
    flag = score_data.get("flag")

    # Score card summary (at top, "下面" = recommendations below)
    top_summaries = {
        (True, True): "各项指标基本在健康范围内，请继续保持良好的睡眠习惯。",
        (True, False): "有一些方面可以改善，看看下面的建议，做出小改变就能带来大不同。",
        (False, True): "关键指标需要重点关注，别担心，下面有具体的改善建议，一步一步来就好。",
        (False, False): "多项指标偏离了健康范围，建议认真看看下面的建议，必要时咨询睡眠专科医生。",
    }
    # Bottom summary (at end, say something different)
    bottom_summaries = {
        (True, True): "你的睡眠整体不错，继续保持就好。偶尔一两天睡不好很正常，不用太在意。",
        (True, False): "睡眠质量还有提升空间，试着从一两个小习惯开始改变，坚持一两周看看效果。",
        (False, True): "改善睡眠是个过程，不用急于求成。按照建议一步步来，身体会慢慢给出反馈。",
        (False, False): "如果尝试了建议但睡眠仍然很差，不妨记录一周的睡眠日记，去看医生时会很有帮助。",
    }

    if total >= 85:
        top = top_summaries[(True, True)]
        bottom = bottom_summaries[(True, True)]
    elif total >= 70:
        top = top_summaries[(True, False)]
        bottom = bottom_summaries[(True, False)]
    elif total >= 50:
        top = top_summaries[(False, True)]
        bottom = bottom_summaries[(False, True)]
    else:
        top = top_summaries[(False, False)]
        bottom = bottom_summaries[(False, False)]

    if flag:
        top += f" 最值得关注的是：{flag}。"

    return {
        "score_summary": f"睡眠得分 {total} 分（{grade}），属于「{grade_label}」水平。",
        "plain_summary": top,
        "bottom_summary": bottom,
        "headline": f"睡眠得分 {total} 分 · {grade_label}",
    }
