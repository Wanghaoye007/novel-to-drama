# Slim Current Repo Review Pack for OpenRouter Fable 5


- Generated: 2026-07-08T16:51:24.757840

- HEAD: `f0962f0`

## Git Status
```
## codex/unify-platform-flow...origin/codex/unify-platform-flow
?? .review_branch_mock/
?? .review_branch_quality/
?? docs/reviews/2026-07-06-openrouter-fable5-current-flow-pack.md
?? docs/reviews/2026-07-06-openrouter-fable5-current-flow-response.json
?? docs/reviews/2026-07-06-openrouter-fable5-current-flow-review-attempt.md
?? docs/reviews/2026-07-08-openrouter-fable5-current-repo-pack.md
```

## Recent Commits
```
f0962f0 fix: scope quality repair instructions by episode
7f3ba03 fix: add ops workers for async exports
1374679 Merge remote-tracking branch 'origin/codex/unify-platform-flow' into codex/unify-platform-flow
0004301 fix: harden async jobs and source context isolation
c6435ee feat: tighten source-grounded generation workflow
fafcedd Finish platform controls and source fidelity gates
5d2a2e5 Strengthen traceable drama quality repair gates
3da0c02 Harden platform generation workflow
ce8664e Harden traceable drama generation workflow
7e71082 Strengthen adaptation quality gates and methodology ingest
381bc51 Omit episode title lines from script exports
4b0c762 Keep round pages polling during batch runs
```

## Review Focus
请作为架构/代码/产品质量总审查，重点看小说转短剧的北极星：输入小说，输出必须显著保留原文 C0/C1、高价值名场面、人物动机、主动方、因果顺序和情绪递进；强原文只允许轻改，不能为了爽点大改或自己编。请输出 P0/P1/P2，精确到文件/函数，并给链路收敛方案。特别关注：
- 第二集以后和原文相差过大、信息丢失、模型自己编。
- source_to_episode_mapping、episode_source_packets、episode_cut_table 是否正确成为生成基准。
- quality gate 是否在生成前约束，而不是事后打分。
- repair 是否会跨集污染或洗掉已写好的内容。
- prompt 是否过重、资产是否重复/冲突、是否需要更优雅收敛。
- 测试是否真实证明质量，而不是 mock 假绿。


## File: `src/novel_drama_engine/pipeline.py`
### Lines 580-660
```
580:         "experiment_mode": experiment_mode_enabled(),
581:         "resume_requested": resume_artifacts_enabled(),
582:         "trace_prompts": prompt_trace_enabled() or experiment_mode_enabled(),
583:         "trace_raw_outputs": raw_output_trace_enabled(),
584:         "cache_fingerprint": _json_fingerprint(fingerprint_payload),
585:     }
586: 
587: 
588: EPISODE_RANGE_PATTERNS = (
589:     re.compile(
590:         r"\bEP\s*0*(\d{1,3})\s*(?:-|~|–|—|至|到)\s*(?:EP\s*)?0*(\d{1,3})\b",
591:         re.IGNORECASE,
592:     ),
593:     re.compile(r"第\s*0*(\d{1,3})\s*(?:-|~|–|—|至|到)\s*0*(\d{1,3})\s*集"),
594: )
595: 
596: EPISODE_REF_PATTERNS = (
597:     re.compile(r"\bEP\s*0*(\d{1,3})\b", re.IGNORECASE),
598:     re.compile(r"第\s*0*(\d{1,3})\s*集"),
599: )
600: 
601: 
602: def episode_numbers_mentioned_in_quality(
603:     quality_report: QualityReport,
604:     valid_episode_numbers: list[int],
605: ) -> set[int]:
606:     valid = set(valid_episode_numbers)
607:     text = "\n".join(
608:         [*quality_report.blocking_issues, quality_report.rewrite_instruction]
609:     )
610:     mentioned: set[int] = set()
611:     for pattern in EPISODE_RANGE_PATTERNS:
612:         for start_text, end_text in pattern.findall(text):
613:             start, end = int(start_text), int(end_text)
614:             if end < start:
615:                 start, end = end, start
616:             mentioned.update(
617:                 number for number in range(start, end + 1) if number in valid
618:             )
619:     for pattern in EPISODE_REF_PATTERNS:
620:         mentioned.update(
621:             number
622:             for number in (int(match) for match in pattern.findall(text))
623:             if number in valid
624:         )
625:     return mentioned
626: 
627: 
628: def source_evidence_targets_for_episode(
629:     quality_report: QualityReport,
630:     episode_number: int,
631: ) -> list[str]:
632:     prefix = f"EP{episode_number:02d}"
633:     text = "\n".join(
634:         [*quality_report.blocking_issues, quality_report.rewrite_instruction]
635:     )
636:     matches = re.findall(
637:         rf"{re.escape(prefix)}\s*缺少原文资产[：:][^；;\n]+",
638:         text,
639:     )
640:     return list(dict.fromkeys(match.strip() for match in matches))
641: 
642: 
643: def quality_instruction_for_episode(
644:     quality_report: QualityReport,
645:     episode_number: int,
646: ) -> str:
647:     merged = merge_rewrite_instructions(
648:         [*quality_report.blocking_issues, quality_report.rewrite_instruction],
649:         blocking=quality_report.status != QualityStatus.USABLE
650:         or bool(quality_report.blocking_issues),
651:     )
652:     return filter_quality_text_for_episode(merged, episode_number)
653: 
654: 
655: def provisional_next_round_context(
656:     script_batch: ScriptBatch,
657:     previous_context: NextRoundContext | None = None,
658: ) -> NextRoundContext:
659:     episodes = sorted(script_batch.episodes, key=lambda item: item.episode)
660:     current_episode = episodes[-1].episode if episodes else 0
```
### Lines 1320-1495
```
1320:                     production_spec=production_spec,
1321:                     source_annotation=source_annotation,
1322:                     episode_cut_table=episode_cut_table,
1323:                 )
1324:             ),
1325:         )
1326:         quality_methodology_context = methodology_context_for(MethodologyStage.QUALITY_GATE)
1327: 
1328:         checker = ContinuityBoomChecker(tracked_llm)
1329:         quality_report = run_stage(
1330:             "quality_report",
1331:             lambda: checker.run(
1332:                 source_analysis,
1333:                 episode_context,
1334:                 story_bible,
1335:                 script_batch,
1336:                 previous_context,
1337:                 viral_asset_report=viral_asset_report,
1338:                 series_structure_plan=series_structure_plan,
1339:                 episode_plan=episode_plan,
1340:                 methodology_context=quality_methodology_context,
1341:             ),
1342:         )
1343: 
1344:         def apply_local_quality_gates(
1345:             current_script_batch: ScriptBatch,
1346:             current_quality_report: QualityReport,
1347:             artifact_prefix: str,
1348:         ) -> QualityReport:
1349:             provisional_context = provisional_next_round_context(
1350:                 current_script_batch,
1351:                 previous_context,
1352:             )
1353:             local_adaptation_quality = run_stage(
1354:                 f"{artifact_prefix}_adaptation_quality",
1355:                 lambda: build_adaptation_quality_report(
1356:                     source_text=source_text,
1357:                     source_analysis=source_analysis,
1358:                     episode_context=episode_context,
1359:                     story_bible=story_bible,
1360:                     script_batch=current_script_batch,
1361:                     next_round_context=provisional_context,
1362:                     previous_context=previous_context,
1363:                     viral_asset_report=viral_asset_report,
1364:                     episode_plan=episode_plan,
1365:                     series_structure_plan=series_structure_plan,
1366:                 ),
1367:             )
1368:             self.store.write_round_artifact(
1369:                 round_number,
1370:                 f"{artifact_prefix}_adaptation_quality",
1371:                 local_adaptation_quality,
1372:             )
1373:             local_methodology_quality = run_stage(
1374:                 f"{artifact_prefix}_methodology_quality",
1375:                 lambda: build_methodology_quality_report(
1376:                     source_analysis=source_analysis,
1377:                     script_batch=current_script_batch,
1378:                     source_strength_profile=source_strength_profile,
1379:                     methodology_context=quality_methodology_context,
1380:                     viral_asset_report=viral_asset_report,
1381:                 ),
1382:             )
1383:             self.store.write_round_artifact(
1384:                 round_number,
1385:                 f"{artifact_prefix}_methodology_quality",
1386:                 local_methodology_quality,
1387:             )
1388:             local_novelty_report = run_stage(
1389:                 f"{artifact_prefix}_script_novelty",
1390:                 lambda: build_script_novelty_report(current_script_batch),
1391:             )
1392:             self.store.write_round_artifact(
1393:                 round_number,
1394:                 f"{artifact_prefix}_script_novelty_report",
1395:                 local_novelty_report,
1396:             )
1397:             self.store.write_text_artifact(
1398:                 round_number,
1399:                 f"{artifact_prefix}_script_novelty_report.md",
1400:                 render_script_novelty_report(local_novelty_report),
1401:             )
1402:             local_source_evidence_report = run_stage(
1403:                 f"{artifact_prefix}_source_evidence",
1404:                 lambda: build_source_evidence_report(
1405:                     current_script_batch,
1406:                     episode_source_packets=episode_source_packets,
1407:                     episode_context=episode_context,
1408:                 ),
1409:             )
1410:             self.store.write_round_artifact(
1411:                 round_number,
1412:                 f"{artifact_prefix}_source_evidence_report",
1413:                 local_source_evidence_report,
1414:             )
1415:             self.store.write_text_artifact(
1416:                 round_number,
1417:                 f"{artifact_prefix}_source_evidence_report.md",
1418:                 render_source_evidence_report(local_source_evidence_report),
1419:             )
1420:             local_drama_quality_report = run_stage(
1421:                 f"{artifact_prefix}_drama_quality",
1422:                 lambda: build_drama_quality_report(
1423:                     script_batch=current_script_batch,
1424:                     quality_report=current_quality_report,
1425:                     adaptation_quality_report=local_adaptation_quality,
1426:                 ),
1427:             )
1428:             self.store.write_round_artifact(
1429:                 round_number,
1430:                 f"{artifact_prefix}_drama_quality_report",
1431:                 local_drama_quality_report,
1432:             )
1433:             self.store.write_text_artifact(
1434:                 round_number,
1435:                 f"{artifact_prefix}_drama_quality_report.md",
1436:                 render_drama_quality_report(local_drama_quality_report),
1437:             )
1438:             gated_report = run_stage(
1439:                 f"{artifact_prefix}_merge_adaptation_quality",
1440:                 lambda: merge_adaptation_quality_into_report(
1441:                     current_quality_report,
1442:                     local_adaptation_quality,
1443:                 ),
1444:             )
1445:             gated_report = run_stage(
1446:                 f"{artifact_prefix}_merge_methodology_quality",
1447:                 lambda: merge_methodology_quality_into_report(
1448:                     gated_report,
1449:                     local_methodology_quality,
1450:                 ),
1451:             )
1452:             gated_report = run_stage(
1453:                 f"{artifact_prefix}_merge_script_novelty",
1454:                 lambda: merge_script_novelty_into_quality_report(
1455:                     gated_report,
1456:                     local_novelty_report,
1457:                 ),
1458:             )
1459:             gated_report = run_stage(
1460:                 f"{artifact_prefix}_merge_source_evidence",
1461:                 lambda: merge_source_evidence_into_quality_report(
1462:                     gated_report,
1463:                     local_source_evidence_report,
1464:                 ),
1465:             )
1466:             gated_report_before_drama = gated_report
1467:             gated_report = run_stage(
1468:                 f"{artifact_prefix}_merge_drama_quality",
1469:                 lambda: merge_drama_quality_into_report(
1470:                     gated_report,
1471:                     local_drama_quality_report,
1472:                 ),
1473:             )
1474:             if (
1475:                 gated_report_before_drama.status == QualityStatus.USABLE
1476:                 and gated_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
1477:                 and artifact_prefix in {"pre_repair", "post_rewrite"}
1478:             ):
1479:                 gated_report = run_stage(
1480:                     f"{artifact_prefix}_mark_drama_quality_repairable",
1481:                     lambda: gated_report.model_copy(
1482:                         update={"status": QualityStatus.NEEDS_REWRITE},
1483:                     ),
1484:                 )
1485:             return gated_report
1486: 
1487:         quality_report = apply_local_quality_gates(
1488:             script_batch,
1489:             quality_report,
1490:             "pre_repair",
1491:         )
1492: 
1493:         def run_episode_repair_cycle(
1494:             current_script_batch: ScriptBatch,
1495:             current_quality_report: QualityReport,
```
### Lines 1500-1915
```
1500:                 current_quality_report,
1501:             )
1502:             current_episodes = {
1503:                 episode.episode: episode for episode in current_script_batch.episodes
1504:             }
1505:             current_episode_repair_packet_records: list[dict[str, object]] = []
1506: 
1507:             def record_current_episode_repair_packet(packet) -> None:
1508:                 current_episode_repair_packet_records.append(
1509:                     packet.model_dump(mode="json")
1510:                 )
1511:                 self.store.write_text_artifact(
1512:                     round_number,
1513:                     "current_episode_repair_packets.json",
1514:                     json.dumps(
1515:                         current_episode_repair_packet_records,
1516:                         ensure_ascii=False,
1517:                         indent=2,
1518:                     ),
1519:                 )
1520: 
1521:             episode_numbers = expected_episode_numbers(
1522:                 round_number=round_number,
1523:                 previous_context=previous_context,
1524:                 target_episode_count=target_episode_count,
1525:                 episodes_per_round=resolved_episodes_per_round,
1526:             )
1527:             cached_repaired_batch = read_cached_artifact(
1528:                 "script_batch_episode_repair",
1529:                 ScriptBatch,
1530:             )
1531:             if cached_repaired_batch is not None:
1532:                 record_cached_stage("episode_repair")
1533:                 repaired_batch = cached_repaired_batch
1534:             else:
1535:                 local_repair_targets = {
1536:                     episode.episode
1537:                     for episode in current_script_batch.episodes
1538:                     if episode.episode in episode_numbers
1539:                     and episode_quality_warnings(episode)
1540:                 }
1541:                 report_repair_targets = episode_numbers_mentioned_in_quality(
1542:                     current_quality_report,
1543:                     episode_numbers,
1544:                 )
1545:                 missing_episode_targets = {
1546:                     episode_number
1547:                     for episode_number in episode_numbers
1548:                     if episode_number not in current_episodes
1549:                 }
1550:                 repair_targets = (
1551:                     local_repair_targets
1552:                     | report_repair_targets
1553:                     | missing_episode_targets
1554:                 )
1555:                 if not repair_targets and not light_source_cost_control:
1556:                     repair_targets = fallback_episode_repair_targets(episode_numbers)
1557: 
1558:                 self.store.write_text_artifact(
1559:                     round_number,
1560:                     "episode_repair_targets.md",
1561:                     "\n".join(
1562:                         [
1563:                             f"EP{episode_number:02d}"
1564:                             for episode_number in sorted(repair_targets)
1565:                         ]
1566:                         or [
1567:                             "none",
1568:                             "全局质检未点名具体集数，本轮未触发逐集重写。",
1569:                         ]
1570:                     ),
1571:                 )
1572:                 if repair_targets:
1573:                     def handoff_changed(
1574:                         before: EpisodeScript | None,
1575:                         after: EpisodeScript,
1576:                     ) -> bool:
1577:                         before_handoff = handoff_from_episode(before)
1578:                         after_handoff = handoff_from_episode(after)
1579:                         if before_handoff is None or after_handoff is None:
1580:                             return before_handoff != after_handoff
1581:                         return (
1582:                             before_handoff.previous_cliffhanger
1583:                             != after_handoff.previous_cliffhanger
1584:                             or before_handoff.previous_final_lines
1585:                             != after_handoff.previous_final_lines
1586:                             or before_handoff.previous_state_update
1587:                             != after_handoff.previous_state_update
1588:                         )
1589: 
1590:                     def repair_episode_sequence() -> list[EpisodeScript]:
1591:                         dynamic_repair_targets = set(repair_targets)
1592:                         repaired: list[EpisodeScript] = []
1593:                         for episode_number in episode_numbers:
1594:                             previous_episode = repaired[-1] if repaired else None
1595:                             if episode_number in dynamic_repair_targets:
1596:                                 existing_episode = current_episodes.get(episode_number)
1597:                                 episode_repair_context = quality_instruction_for_episode(
1598:                                     current_quality_report,
1599:                                     episode_number,
1600:                                 )
1601:                                 current_repair_packet = (
1602:                                     build_current_episode_repair_packet(
1603:                                         existing_episode,
1604:                                         episode_repair_context,
1605:                                         allow_full_rewrite=not light_source_cost_control,
1606:                                         source_evidence_targets=(
1607:                                             source_evidence_targets_for_episode(
1608:                                                 current_quality_report,
1609:                                                 episode_number,
1610:                                             )
1611:                                         ),
1612:                                     )
1613:                                     if existing_episode is not None
1614:                                     else None
1615:                                 )
1616:                                 if current_repair_packet is not None:
1617:                                     record_current_episode_repair_packet(
1618:                                         current_repair_packet,
1619:                                     )
1620:                                 episode = script_generator.run_episode(
1621:                                     source_text,
1622:                                     source_analysis,
1623:                                     episode_context,
1624:                                     story_bible,
1625:                                     previous_context,
1626:                                     existing_episode,
1627:                                     episode_number,
1628:                                     repair_instruction_for_episode(
1629:                                         episode_number,
1630:                                         existing_episode,
1631:                                         episode_repair_context,
1632:                                     ),
1633:                                     episode_plan=episode_plan,
1634:                                     viral_asset_report=viral_asset_report,
1635:                                     series_structure_plan=series_structure_plan,
1636:                                     methodology_context=script_methodology_context,
1637:                                     episode_source_packet=packet_for_episode(
1638:                                         episode_source_packets,
1639:                                         episode_number,
1640:                                     ),
1641:                                     previous_episode_handoff=handoff_from_episode(
1642:                                         previous_episode,
1643:                                     ),
1644:                                     current_episode_repair_packet=current_repair_packet,
1645:                                     production_spec=production_spec,
1646:                                     source_annotation=source_annotation,
1647:                                     episode_cut_table=episode_cut_table,
1648:                                 )
1649:                                 if (
1650:                                     not episode_quality_warnings(episode)
1651:                                     and handoff_changed(
1652:                                         current_episodes.get(episode_number),
1653:                                         episode,
1654:                                     )
1655:                                     and episode_number + 1 in episode_numbers
1656:                                 ):
1657:                                     dynamic_repair_targets.add(episode_number + 1)
1658:                             else:
1659:                                 episode = current_episodes[episode_number]
1660:                             repaired.append(episode)
1661:                         return repaired
1662: 
1663:                     repaired_episodes = run_stage(
1664:                         "episode_repair",
1665:                         repair_episode_sequence,
1666:                     )
1667:                     repaired_batch = run_stage(
1668:                         "apply_episode_repair",
1669:                         lambda: current_script_batch.model_copy(
1670:                             update={"episodes": repaired_episodes},
1671:                         ),
1672:                     )
1673:                 else:
1674:                     record_skipped_stage(
1675:                         "episode_repair",
1676:                         "Strong-source cost control blocked fallback repair."
1677:                         if light_source_cost_control
1678:                         else "No local, reported, missing, or fallback episode targets.",
1679:                     )
1680:                     repaired_batch = current_script_batch
1681:                     return repaired_batch, current_quality_report
1682:                 self.store.write_round_artifact(
1683:                     round_number,
1684:                     "script_batch_episode_repair",
1685:                     repaired_batch,
1686:                 )
1687: 
1688:             episodes_after_repair = {
1689:                 episode.episode: episode for episode in repaired_batch.episodes
1690:             }
1691:             episodes_needing_polish = {
1692:                 episode_number
1693:                 for episode_number, episode in episodes_after_repair.items()
1694:                 if episode_quality_warnings(episode)
1695:             }
1696:             if episodes_needing_polish:
1697:                 cached_polished_batch = read_cached_artifact(
1698:                     "script_batch_episode_polish",
1699:                     ScriptBatch,
1700:                 )
1701:                 if cached_polished_batch is not None:
1702:                     record_cached_stage("episode_quality_polish")
1703:                     repaired_batch = cached_polished_batch
1704:                 else:
1705:                     polish_instructions = [
1706:                         f"EP{episode_number:02d}: "
1707:                         + repair_instruction_for_episode(
1708:                             episode_number,
1709:                             episodes_after_repair[episode_number],
1710:                             quality_instruction_for_episode(
1711:                                 current_quality_report,
1712:                                 episode_number,
1713:                             ),
1714:                         )
1715:                         for episode_number in sorted(episodes_needing_polish)
1716:                     ]
1717:                     self.store.write_text_artifact(
1718:                         round_number,
1719:                         "episode_polish_instructions.md",
1720:                         "\n\n---\n\n".join(polish_instructions),
1721:                     )
1722:                     if (
1723:                         not blocking_optional_polish_enabled()
1724:                         or light_source_cost_control
1725:                     ):
1726:                         record_skipped_stage(
1727:                             "episode_quality_polish",
1728:                             "Strong-source cost control keeps local polish as "
1729:                             "review-only."
1730:                             if light_source_cost_control
1731:                             else "Set NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH=1 "
1732:                             "to run this pass inline.",
1733:                         )
1734:                     else:
1735:                         episode_polish_failures: list[str] = []
1736: 
1737:                         def polish_episode_or_keep(
1738:                             episode_number: int,
1739:                         ) -> EpisodeScript:
1740:                             if episode_number not in episodes_needing_polish:
1741:                                 return episodes_after_repair[episode_number]
1742:                             existing_episode = episodes_after_repair.get(episode_number)
1743:                             episode_repair_context = quality_instruction_for_episode(
1744:                                 current_quality_report,
1745:                                 episode_number,
1746:                             )
1747:                             current_repair_packet = (
1748:                                 build_current_episode_repair_packet(
1749:                                     existing_episode,
1750:                                     episode_repair_context,
1751:                                     allow_full_rewrite=not light_source_cost_control,
1752:                                     source_evidence_targets=(
1753:                                         source_evidence_targets_for_episode(
1754:                                             current_quality_report,
1755:                                             episode_number,
1756:                                         )
1757:                                     ),
1758:                                 )
1759:                                 if existing_episode is not None
1760:                                 else None
1761:                             )
1762:                             if current_repair_packet is not None:
1763:                                 record_current_episode_repair_packet(current_repair_packet)
1764:                             try:
1765:                                 return script_generator.run_episode(
1766:                                     source_text,
1767:                                     source_analysis,
1768:                                     episode_context,
1769:                                     story_bible,
1770:                                     previous_context,
1771:                                     existing_episode,
1772:                                     episode_number,
1773:                                     repair_instruction_for_episode(
1774:                                         episode_number,
1775:                                         existing_episode,
1776:                                         episode_repair_context,
1777:                                     ),
1778:                                     episode_plan=episode_plan,
1779:                                     viral_asset_report=viral_asset_report,
1780:                                     series_structure_plan=series_structure_plan,
1781:                                     methodology_context=script_methodology_context,
1782:                                     episode_source_packet=packet_for_episode(
1783:                                         episode_source_packets,
1784:                                         episode_number,
1785:                                     ),
1786:                                     previous_episode_handoff=handoff_from_episode(
1787:                                         episodes_after_repair.get(episode_number - 1),
1788:                                     ),
1789:                                     current_episode_repair_packet=current_repair_packet,
1790:                                     production_spec=production_spec,
1791:                                     source_annotation=source_annotation,
1792:                                     episode_cut_table=episode_cut_table,
1793:                                 )
1794:                             except Exception as exc:
1795:                                 episode_polish_failures.append(
1796:                                     f"EP{episode_number:02d}: {exc}"
1797:                                 )
1798:                                 return episodes_after_repair[episode_number]
1799: 
1800:                         polished_episodes = run_stage(
1801:                             "episode_quality_polish",
1802:                             lambda: [
1803:                                 polish_episode_or_keep(episode_number)
1804:                                 for episode_number in episode_numbers
1805:                             ],
1806:                         )
1807:                         if episode_polish_failures:
1808:                             self.store.write_text_artifact(
1809:                                 round_number,
1810:                                 "episode_quality_polish_failures.md",
1811:                                 "\n".join(episode_polish_failures),
1812:                             )
1813:                         repaired_batch = run_stage(
1814:                             "apply_episode_quality_polish",
1815:                             lambda: repaired_batch.model_copy(
1816:                                 update={"episodes": polished_episodes},
1817:                             ),
1818:                         )
1819:                         self.store.write_round_artifact(
1820:                             round_number,
1821:                             "script_batch_episode_polish",
1822:                             repaired_batch,
1823:                         )
1824: 
1825:             episodes_after_quality_polish = {
1826:                 episode.episode: episode for episode in repaired_batch.episodes
1827:             }
1828:             episodes_needing_hook_dialogue = {
1829:                 episode_number
1830:                 for episode_number, episode in episodes_after_quality_polish.items()
1831:                 if episode_needs_hook_dialogue_polish(episode)
1832:             }
1833:             if episodes_needing_hook_dialogue:
1834:                 cached_hook_dialogue_batch = read_cached_artifact(
1835:                     "script_batch_hook_dialogue_polish",
1836:                     ScriptBatch,
1837:                 )
1838:                 if cached_hook_dialogue_batch is not None:
1839:                     record_cached_stage("hook_dialogue_polish")
1840:                     repaired_batch = cached_hook_dialogue_batch
1841:                 else:
1842:                     hook_dialogue_instructions = [
1843:                         f"EP{episode_number:02d}: "
1844:                         + hook_dialogue_polish_instruction(
1845:                             episodes_after_quality_polish[episode_number],
1846:                             quality_instruction_for_episode(
1847:                                 current_quality_report,
1848:                                 episode_number,
1849:                             ),
1850:                         )
1851:                         for episode_number in sorted(episodes_needing_hook_dialogue)
1852:                     ]
1853:                     self.store.write_text_artifact(
1854:                         round_number,
1855:                         "hook_dialogue_polish_instructions.md",
1856:                         "\n\n---\n\n".join(hook_dialogue_instructions),
1857:                     )
1858:                     if (
1859:                         not blocking_optional_polish_enabled()
1860:                         or light_source_cost_control
1861:                     ):
1862:                         record_skipped_stage(
1863:                             "hook_dialogue_polish",
1864:                             "Strong-source cost control keeps hook/dialogue polish "
1865:                             "as review-only."
1866:                             if light_source_cost_control
1867:                             else "Set NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH=1 "
1868:                             "to run this pass inline.",
1869:                         )
1870:                     else:
1871:                         hook_dialogue_failures: list[str] = []
1872: 
1873:                         def hook_dialogue_episode_or_keep(
1874:                             episode_number: int,
1875:                         ) -> EpisodeScript:
1876:                             if episode_number not in episodes_needing_hook_dialogue:
1877:                                 return episodes_after_quality_polish[episode_number]
1878:                             episode_repair_context = quality_instruction_for_episode(
1879:                                 current_quality_report,
1880:                                 episode_number,
1881:                             )
1882:                             current_repair_packet = build_current_episode_repair_packet(
1883:                                 episodes_after_quality_polish[episode_number],
1884:                                 episode_repair_context,
1885:                                 allow_full_rewrite=not light_source_cost_control,
1886:                                 source_evidence_targets=(
1887:                                     source_evidence_targets_for_episode(
1888:                                         current_quality_report,
1889:                                         episode_number,
1890:                                     )
1891:                                 ),
1892:                             )
1893:                             record_current_episode_repair_packet(current_repair_packet)
1894:                             try:
1895:                                 return script_generator.run_episode_hook_dialogue_polish(
1896:                                     source_text,
1897:                                     source_analysis,
1898:                                     episode_context,
1899:                                     story_bible,
1900:                                     previous_context,
1901:                                     episodes_after_quality_polish[episode_number],
1902:                                     episode_number,
1903:                                     hook_dialogue_polish_instruction(
1904:                                         episodes_after_quality_polish[episode_number],
1905:                                         episode_repair_context,
1906:                                     ),
1907:                                     episode_plan=episode_plan,
1908:                                     viral_asset_report=viral_asset_report,
1909:                                     series_structure_plan=series_structure_plan,
1910:                                     methodology_context=script_methodology_context,
1911:                                     episode_source_packet=packet_for_episode(
1912:                                         episode_source_packets,
1913:                                         episode_number,
1914:                                     ),
1915:                                     previous_episode_handoff=handoff_from_episode(
```
### Lines 1960-2075
```
1960:                 lambda: checker.run(
1961:                     source_analysis,
1962:                     episode_context,
1963:                     story_bible,
1964:                     repaired_batch,
1965:                     previous_context,
1966:                     viral_asset_report=viral_asset_report,
1967:                     series_structure_plan=series_structure_plan,
1968:                     episode_plan=episode_plan,
1969:                     methodology_context=quality_methodology_context,
1970:                 ),
1971:             )
1972:             repaired_quality = apply_local_quality_gates(
1973:                 repaired_batch,
1974:                 repaired_quality,
1975:                 "post_episode_repair",
1976:             )
1977:             if repaired_quality.status == QualityStatus.NEEDS_REWRITE:
1978:                 repaired_quality = run_stage(
1979:                     "mark_human_review_after_episode_repair",
1980:                     lambda: repaired_quality.model_copy(
1981:                         update={"status": QualityStatus.NEEDS_HUMAN_REVIEW},
1982:                     ),
1983:                 )
1984:             return repaired_batch, repaired_quality
1985: 
1986:         if (
1987:             quality_report.status == QualityStatus.NEEDS_REWRITE
1988:             and effective_repair_budget != RepairBudget.NONE
1989:         ):
1990:             self.store.write_round_artifact(
1991:                 round_number,
1992:                 "quality_report_before_rewrite",
1993:                 quality_report,
1994:             )
1995:             if (
1996:                 effective_repair_budget == RepairBudget.EPISODE
1997:             ):
1998:                 script_batch, quality_report = run_episode_repair_cycle(
1999:                     script_batch,
2000:                     quality_report,
2001:                 )
2002:             else:
2003:                 script_batch = cached_stage(
2004:                     "script_batch_rewrite",
2005:                     "script_batch_rewrite",
2006:                     ScriptBatch,
2007:                     lambda: script_generator.run(
2008:                         source_text,
2009:                         source_analysis,
2010:                         episode_context,
2011:                         story_bible,
2012:                         previous_context,
2013:                         quality_report.rewrite_instruction,
2014:                         round_number,
2015:                         target_episode_count,
2016:                         episode_plan=episode_plan,
2017:                         viral_asset_report=viral_asset_report,
2018:                         series_structure_plan=series_structure_plan,
2019:                         methodology_context=script_methodology_context,
2020:                         episode_source_packets=episode_source_packets,
2021:                         production_spec=production_spec,
2022:                         source_annotation=source_annotation,
2023:                         episode_cut_table=episode_cut_table,
2024:                     ),
2025:                 )
2026:                 quality_report = run_stage(
2027:                     "quality_report_after_rewrite",
2028:                     lambda: checker.run(
2029:                         source_analysis,
2030:                         episode_context,
2031:                         story_bible,
2032:                         script_batch,
2033:                         previous_context,
2034:                         viral_asset_report=viral_asset_report,
2035:                         series_structure_plan=series_structure_plan,
2036:                         episode_plan=episode_plan,
2037:                         methodology_context=quality_methodology_context,
2038:                     ),
2039:                 )
2040:                 quality_report = apply_local_quality_gates(
2041:                     script_batch,
2042:                     quality_report,
2043:                     "post_rewrite",
2044:                 )
2045:                 if (
2046:                     quality_report.status == QualityStatus.NEEDS_REWRITE
2047:                     and effective_repair_budget == RepairBudget.EPISODE
2048:                 ):
2049:                     script_batch, quality_report = run_episode_repair_cycle(
2050:                         script_batch,
2051:                         quality_report,
2052:                     )
2053:                 elif quality_report.status == QualityStatus.NEEDS_REWRITE:
2054:                     quality_report = run_stage(
2055:                         "mark_human_review_after_rewrite_budget",
2056:                         lambda: quality_report.model_copy(
2057:                             update={"status": QualityStatus.NEEDS_HUMAN_REVIEW},
2058:                         ),
2059:                     )
2060:         elif quality_report.status == QualityStatus.NEEDS_REWRITE:
2061:             quality_report = run_stage(
2062:                 "mark_human_review_without_repair",
2063:                 lambda: quality_report.model_copy(
2064:                     update={"status": QualityStatus.NEEDS_HUMAN_REVIEW},
2065:                 ),
2066:             )
2067: 
2068:         self.store.write_round_artifact(round_number, "quality_report", quality_report)
2069: 
2070:         next_round_context = run_stage(
2071:             "next_round_context",
2072:             lambda: StateWriter(tracked_llm).run(
2073:                 source_analysis,
2074:                 episode_context,
2075:                 story_bible,
```

## File: `src/novel_drama_engine/prompts.py`
### Lines 930-1055
```
930:     target_episode_count: int | None = None,
931:     episode_plan: BaseModel | None = None,
932:     viral_asset_report: BaseModel | None = None,
933:     series_structure_plan: BaseModel | None = None,
934:     methodology_context: MethodologyContext | None = None,
935:     episode_source_packets: BaseModel | None = None,
936:     production_spec: BaseModel | None = None,
937:     source_annotation: BaseModel | None = None,
938:     episode_cut_table: BaseModel | None = None,
939: ) -> str:
940:     target_text = str(target_episode_count) if target_episode_count else "未指定"
941:     if script_prompt_mode() == "creative":
942:         return prompt_block(
943:             source_material_section(
944:                 source_text,
945:                 episode_source_packets=episode_source_packets,
946:             ),
947:             f"当前轮次：第 {round_number} 轮",
948:             f"目标总集数：{target_text}",
949:             section("本轮集数硬清单", episode_range_contract(episode_context)),
950:             lean_flow_authority_section(),
951:             dump_model("production_spec", production_spec),
952:             dump_model("source_annotation", source_annotation),
953:             dump_model("episode_cut_table", episode_cut_table),
954:             script_reference_context_section(
955:                 source_analysis=source_analysis,
956:                 episode_context=episode_context,
957:                 previous_context=previous_context,
958:                 viral_asset_report=viral_asset_report,
959:                 series_structure_plan=series_structure_plan,
960:             ),
961:             dump_model("story_bible", story_bible),
962:             dump_model("episode_plan", episode_plan),
963:             f"rewrite_instruction: {rewrite_instruction}",
964:             section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
965:             section("内部方法论", render_methodology_context(methodology_context)),
966:             section("生成期源文保真硬指标", SOURCE_FIDELITY_GENERATION_RULE),
967:             stage_instruction(
968:                 "输出 episode_context.target_episode_range 覆盖的全部 EpisodeScript。先写创作稿质量：一场戏要成立，再考虑后续执行稿补镜头。",
969:                 (
970:                     "逐集先确认原文片段、C0 不可改事实、C1 必保名场面、Story Bible 人物动机和 episode_plan 的本集目标；"
971:                     "source packet 是当前集原文边界，EpisodeDramaPlan 只能在当前集 source packet 边界内执行；"
972:                     "若 episode_plan 的动作、道具、证据、台词或断点无法在当前集 packet.source_excerpt/C0/C1/C2 中追溯，必须丢弃或改回原文当前集。"
973:                     "再决定哪些内心戏转成动作/OS/短对白，哪些过渡删除，哪些钩子需要事实兼容地补强。"
974:                     "如果 series_structure_plan 不为空，必须对齐本集核心事件、信息增量、断点类型和原文锚点。"
975:                 ),
976:                 (
977:                     "必须输出 ScriptBatch schema。每集填写 episode/title/hook_3s/main_emotion/watch_reason/scenes/cliffhanger/state_update；"
978:                     "hook_3s/main_emotion/watch_reason 是内部字段，不能作为用户可见说明行。"
979:                     "Hook/main_emotion/watch_reason/消费理由只允许出现在 EpisodeScript 结构化字段中。"
980:                     "Hook/main_emotion/watch_reason/消费理由不得出现在任何 scene.lines 的 action/dialogue/os/vo/transition 文本里。"
981:                     "scenes 是正片创作稿：scene.heading 必须严格写成“集数-场次 日/夜-内/外-具体地点”；"
982:                     "禁止只写 豪华宴会厅、走廊、房间、街上 这类泛化场景头。"
983:                     "action 写可看见的动作、道具、表情、空间压迫、声音或转场，但不要为了凑指标堆景别运镜；"
984:                     "dialogue/os/vo 必须短、像真人、带潜台词，不能用长句解释背景。"
985:                     "执行稿参考密度：每集 scene.lines 合计至少 28 行可在 shooting repair 阶段补齐，首稿优先保证戏成立。"
986:                     f"{VISIBLE_SCRIPT_DENSITY_RULE}"
987:                     "后置执行稿参考：每条 action 必须写清景别、主体位置、镜头运动、构图/光线、关键道具、人物表情、声音/BGM 或镜头衔接；"
988:                     "每条 action 必须显式包含一个景别词和一个运镜词，但首稿优先保证动作因果和人物状态。"
989:                     f"{ACTION_LINE_TEMPLATE_RULE}{SHOT_LINKAGE_RULE}{FINAL_TWO_LINE_RULE}{INFO_INCREMENT_RULE}"
990:                     "对白一句不超过 22 个汉字，只表达一个动作或情绪。"
991:                     "不合格 action 示例：△武植在床上睁开眼。/ △宴会厅内，灯光璀璨，众人震惊。"
992:                 ),
993:                 (
994:                     "第一场前三行必须让观众立刻看到冲突/危险/羞辱/误会/反差/强选择之一。"
995:                     "如果原文已有天然钩子，第一场必须保留其核心张力并合规视听化；如果原文没有钩子，只补不违背事实和动机的事实兼容型钩子。"
996:                     "每集至少有一次情绪转向或信息增量，结尾必须停在观众最想看下一秒的位置。"
997:                     "cliffhanger 字段必须直接填写最后一场最后 4 行里已经演出来的钩子台词或动作。"
998:                 ),
999:                 (
1000:                     "禁止改变主角核心动机、主动方、关键决定时机、证据来源和关系状态。"
1001:                     "禁止为了爽点新增无原文依据的道具、狠话、身份、资本解法或法务结果。"
1002:                     "禁止把克制人物写成歇斯底里，把深思熟虑写成临场冲动，把对手主动欺骗改成主角主动索要。"
1003:                     "最后一场最后 2 行必须把 cliffhanger 以对白、动作或道具特写演出来。"
1004:                     "禁止旁白式总结、价值观说明、消费理由说明、观众要看、本集看点、本集钩子等外露分析。"
1005:                     "禁止外露“3秒 Hook/主情绪/消费理由/观众要看/本集看点”。"
1006:                 ),
1007:             ),
1008:         )
1009:     return prompt_block(
1010:         source_material_section(
1011:             source_text,
1012:             episode_source_packets=episode_source_packets,
1013:         ),
1014:         f"当前轮次：第 {round_number} 轮",
1015:         f"目标总集数：{target_text}",
1016:         section("本轮集数硬清单", episode_range_contract(episode_context)),
1017:         lean_flow_authority_section(),
1018:         dump_model("production_spec", production_spec),
1019:         dump_model("source_annotation", source_annotation),
1020:         dump_model("episode_cut_table", episode_cut_table),
1021:         script_reference_context_section(
1022:             source_analysis=source_analysis,
1023:             episode_context=episode_context,
1024:             previous_context=previous_context,
1025:             viral_asset_report=viral_asset_report,
1026:             series_structure_plan=series_structure_plan,
1027:         ),
1028:         dump_model("story_bible", story_bible),
1029:         dump_model("episode_plan", episode_plan),
1030:         f"rewrite_instruction: {rewrite_instruction}",
1031:         section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
1032:         section("内部方法论", render_methodology_context(methodology_context)),
1033:         section("生成期源文保真硬指标", SOURCE_FIDELITY_GENERATION_RULE),
1034:         stage_instruction(
1035:             "必须输出 episode_context.target_episode_range 覆盖的全部集数，最多 5 集。",
1036:             (
1037:                 "逐集先读 EpisodeDramaPlan 和 SeriesEpisodeOutline，确认本集核心事件、信息增量、断点类型和原文锚点；"
1038:                 "source packet 是当前集原文边界，EpisodeDramaPlan 只能在当前集 source packet 边界内执行；"
1039:                 "若计划动作、道具、证据或断点不属于当前集 packet.source_excerpt/C0/C1/C2，必须丢弃或改回原文当前集；"
1040:                 "再按原文资产分级决定“保护 C0/C1、视听化 C2、压缩 C3、删除 C4”，"
1041:                 "最后写前三秒可见冲突、三波拉扯、假打脸/钥匙兑现、反派最后一装和结尾截断。"
1042:             ),
1043:             (
1044:                 "如果 episode_plan 不为空，只能在当前集 source packet 边界内逐集执行对应 EpisodeDramaPlan：drama_engine 决定本集动作逻辑，"
1045:                 "three_pull_beats 决定场景推进，false_payoff/planted_key/cliffhanger_design 必须在剧本中兑现或预埋。"
1046:                 "如果 series_structure_plan 不为空，必须逐集执行对应 SeriesEpisodeOutline 的核心事件、信息增量、断点类型和原文锚点；"
1047:                 "不能为了写爽点而断开全剧结构。如果 viral_asset_report 不为空，至少保留本轮相关名场面/金句/情绪资产，"
1048:                 "并按 risk_treatments 避开敏感设定和慢热支线。"
1049:                 "如果原文已有 C1 天然钩子，第一场必须保留其核心张力并合规视听化；"
1050:                 "如果原文没有天然钩子，第一场必须补事实兼容型钩子，并在动作/对白里能追溯到 source_anchor 或 C0/C1/C2。"
1051:                 "任何新增动作、道具、证据、狠话都必须只补镜头或衔接，不能改变主角欲望、主动方、因果顺序或关键决定时机。"
1052:                 "必须执行事件账本：同一高价值名场面不能跨集重复兑现；身份/机构/舆论/权威裁决类结果必须先写清证据来源和流程，再写结果。"
1053:                 "episode 字段必须是数字集数；scene.heading 必须严格写成 “集数-场次 日/夜-内/外-具体地点”，例如 1-1 夜-内-武家卧室，"
1054:                 "禁止只写 豪华宴会厅、走廊、房间、街上 这类泛化场景头。"
1055:             ),
```
### Lines 1100-1265
```
1100:     episode_context: BaseModel,
1101:     story_bible: BaseModel,
1102:     previous_context: BaseModel | None,
1103:     existing_episode: BaseModel | None,
1104:     episode_number: int,
1105:     rewrite_instruction: str,
1106:     episode_plan: BaseModel | None = None,
1107:     viral_asset_report: BaseModel | None = None,
1108:     series_structure_plan: BaseModel | None = None,
1109:     methodology_context: MethodologyContext | None = None,
1110:     episode_source_packet: BaseModel | None = None,
1111:     previous_episode_handoff: BaseModel | None = None,
1112:     current_episode_repair_packet: BaseModel | None = None,
1113:     production_spec: BaseModel | None = None,
1114:     source_annotation: BaseModel | None = None,
1115:     episode_cut_table: BaseModel | None = None,
1116: ) -> str:
1117:     return prompt_block(
1118:         source_material_section(
1119:             source_text,
1120:             episode_source_packet=episode_source_packet,
1121:         ),
1122:         f"只生成第 {episode_number} 集。不要输出其他集数。",
1123:         lean_flow_authority_section(),
1124:         dump_model("production_spec", production_spec),
1125:         dump_model("source_annotation", source_annotation),
1126:         dump_model("episode_cut_table", episode_cut_table),
1127:         dump_model("previous_episode_handoff", previous_episode_handoff),
1128:         script_reference_context_section(
1129:             source_analysis=source_analysis,
1130:             episode_context=episode_context,
1131:             previous_context=previous_context,
1132:             viral_asset_report=viral_asset_report,
1133:             series_structure_plan=series_structure_plan,
1134:         ),
1135:         dump_model("story_bible", story_bible),
1136:         dump_model("existing_episode_to_rewrite", existing_episode),
1137:         dump_model("current_episode_repair_packet", current_episode_repair_packet),
1138:         dump_model("episode_plan", episode_plan),
1139:         f"rewrite_instruction: {rewrite_instruction}",
1140:         section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
1141:         section("内部方法论", render_methodology_context(methodology_context)),
1142:         section("生成期源文保真硬指标", SOURCE_FIDELITY_GENERATION_RULE),
1143:         stage_instruction(
1144:             (
1145:                 f"输出必须是一个 EpisodeScript；episode 字段必须等于 {episode_number}。"
1146:                 "这是按问题类型执行的定向修复，不是默认整集重写。"
1147:                 "必须先读取 rewrite_instruction 里的“修复级别”，再决定允许改动范围。"
1148:                 "如果 current_episode_repair_packet 不为空，必须优先遵守 current_episode_repair_packet.allowed_change_scope。"
1149:             ),
1150:             (
1151:                 "先定位 existing_episode 的失败点和 rewrite_instruction 的硬伤；"
1152:                 "如果修复级别是格式局部修复，只修不合格 action/标题/外露分析行；"
1153:                 "如果是结尾钩子局部修复，只修最后一场最后 8-12 行和必要短对白；"
1154:                 "如果是单集创作修复，才回到本集 EpisodeDramaPlan / SeriesEpisodeOutline / source packet "
1155:                 "修 OOC、原文偏离、情绪递进或冲突因果；"
1156:                 "只有修复级别明确写结构崩坏整集重写时，才允许重写整集。"
1157:             ),
1158:             (
1159:                 "如果 episode_plan 不为空，必须优先执行本集 EpisodeDramaPlan 的 drama_engine、"
1160:                 "three_pull_beats、false_payoff、planted_key、strongest_line 和 cliffhanger_design。"
1161:                 "source packet 是当前集原文边界，EpisodeDramaPlan 只能在当前集 source packet 边界内执行；"
1162:                 "若计划项和 packet.source_excerpt/C0/C1/C2 冲突，必须服从 source packet；"
1163:                 "existing_episode 只有在可被当前集 source packet/source_annotation 证明时才可保留。"
1164:                 "如果 series_structure_plan 不为空，必须对齐本集 SeriesEpisodeOutline 的 "
1165:                 "core_event、information_increment、ending_hook_type 和 source_anchor。"
1166:                 "如果 episode_source_packet 不为空，必须优先使用 packet.source_excerpt 和 C0/C1/C2/C4，"
1167:                 "不得从全文或其他集 packet 自由补剧情。"
1168:                 "如果 previous_episode_handoff 不为空，第一场前 3-6 行必须照应上一集最后钩子，"
1169:                 "不能重开一个无关场面。"
1170:                 f"{repair_packet_baseline_instruction(current_episode_repair_packet)}"
1171:                 "定向修复必须是“回到原文资产 + 修指定缺口”，不能把修复写成新剧情或整集洗稿。"
1172:                 "若 existing_episode 删除了 C1 天然钩子，要恢复并合规视听化；若原文没有天然钩子，只能补事实兼容型钩子。"
1173:                 "必须删除 C4 编造动作/道具/台词，尤其是改变主动方、动机、关键决定时机、证据来源或关系状态的内容。"
1174:                 f"scene.heading 必须严格写成 “{episode_number}-场次 日/夜-内/外-具体地点”，例如 {episode_number}-1 夜-内-武家卧室。"
1175:                 "只有结构崩坏整集重写时才强制执行完整密度目标。"
1176:                 f"{VISIBLE_SCRIPT_DENSITY_RULE}"
1177:                 "局部修复时保留 existing_episode 已合格密度，不要为了补指标增加水对白、空镜或新支线。"
1178:             ),
1179:             (
1180:                 "第一场前 8 个 beat 必须有危机、误会、羞辱、威胁或强反击。"
1181:                 "每条 action 必须以 △ 开头，并写清景别、主体位置、镜头运动、构图/光线、关键道具、"
1182:                 "人物表情、音效/BGM 触发和切镜衔接。每条 action 必须显式包含一个景别词"
1183:                 "（全景/中景/中近景/近景/特写/俯拍/仰拍/长焦）和一个运镜词"
1184:                 "（推近/拉远/横移/跟拍/摇向/甩向/切到/扫过/快剪/拉焦/环绕/上移/定格/慢镜头）。"
1185:                 f"{ACTION_LINE_TEMPLATE_RULE}"
1186:                 f"{SHOT_LINKAGE_RULE}"
1187:                 f"{INFO_INCREMENT_RULE}"
1188:                 "OS 后必须紧跟物理动作或明确决定；对白一句不超过 22 个汉字，只表达一个动作或情绪。"
1189:                 "hook_3s/main_emotion/watch_reason 只是内部字段，必须把 hook 融入第一场的动作、OS/VO 或对白。"
1190:                 "cliffhanger 字段必须直接填写最后一场最后 4 行里已经演出来的钩子台词或动作，"
1191:                 "禁止写成“留下悬念/关于身份的悬念/气氛紧张”等说明句。"
1192:                 "Hook/main_emotion/watch_reason/消费理由不得出现在任何 scene line 文本里。"
1193:                 "结尾钩子必须是强疑问、威胁、反转或动作未完成，并在最后一场最后 2 行演出来；"
1194:                 "最后两行不能是“结尾钩子/看点/消费理由”的说明文字。"
1195:                 f"{FINAL_TWO_LINE_RULE}"
1196:             ),
1197:             (
1198:                 "禁止写“△ 武植在床上睁开眼”这种无景别、无运镜的动作行。"
1199:                 "禁止为了修复烈度而改变 C0，禁止把预谋改成冲动、把被动承受改成主动索取、把克制人物改成歇斯底里。"
1200:                 "不能出现“3秒 Hook/主情绪/消费理由/观众要看/本集看点”等外露分析。"
1201:                 "不能为了修复字数而加背景介绍、价值观总结、泛场景、空镜拖时或解释型长对白。"
1202:                 "不能用黑屏、转场、画面定格、普通 OS 作为最后两行钩子。"
1203:                 "如果原文是男频穿越/大宋/武大郎/金莲/西门庆类，修复必须回到现代认知差、轻喜误会反转、"
1204:                 "护妻/经商打脸，不能套真假千金、豪门宴会、总裁认亲模板。"
1205:             ),
1206:         ),
1207:     )
1208: 
1209: 
1210: def hook_dialogue_polish_user(
1211:     source_text: str | None,
1212:     source_analysis: BaseModel,
1213:     episode_context: BaseModel,
1214:     story_bible: BaseModel,
1215:     previous_context: BaseModel | None,
1216:     existing_episode: BaseModel,
1217:     episode_number: int,
1218:     polish_instruction: str,
1219:     episode_plan: BaseModel | None = None,
1220:     viral_asset_report: BaseModel | None = None,
1221:     series_structure_plan: BaseModel | None = None,
1222:     methodology_context: MethodologyContext | None = None,
1223:     episode_source_packet: BaseModel | None = None,
1224:     previous_episode_handoff: BaseModel | None = None,
1225:     current_episode_repair_packet: BaseModel | None = None,
1226:     production_spec: BaseModel | None = None,
1227:     source_annotation: BaseModel | None = None,
1228:     episode_cut_table: BaseModel | None = None,
1229: ) -> str:
1230:     return prompt_block(
1231:         source_material_section(
1232:             source_text,
1233:             episode_source_packet=episode_source_packet,
1234:         ),
1235:         f"只二次编译第 {episode_number} 集的结尾钩子和对白密度。不要输出其他集数。",
1236:         lean_flow_authority_section(),
1237:         dump_model("production_spec", production_spec),
1238:         dump_model("source_annotation", source_annotation),
1239:         dump_model("episode_cut_table", episode_cut_table),
1240:         dump_model("previous_episode_handoff", previous_episode_handoff),
1241:         script_reference_context_section(
1242:             source_analysis=source_analysis,
1243:             episode_context=episode_context,
1244:             previous_context=previous_context,
1245:             viral_asset_report=viral_asset_report,
1246:             series_structure_plan=series_structure_plan,
1247:         ),
1248:         dump_model("story_bible", story_bible),
1249:         dump_model("existing_episode_to_polish", existing_episode),
1250:         dump_model("current_episode_repair_packet", current_episode_repair_packet),
1251:         dump_model("episode_plan", episode_plan),
1252:         f"polish_instruction: {polish_instruction}",
1253:         section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
1254:         section("内部方法论", render_methodology_context(methodology_context)),
1255:         section("生成期源文保真硬指标", SOURCE_FIDELITY_GENERATION_RULE),
1256:         stage_instruction(
1257:             (
1258:                 f"输出必须是一个完整 EpisodeScript；episode 字段必须等于 {episode_number}。"
1259:                 "这是结尾钩子/对白密度二次编译，不是整集重写；不要整集重写。"
1260:                 "如果 current_episode_repair_packet 不为空，必须先读取 baseline_policy 决定修复基准。"
1261:             ),
1262:             (
1263:                 "先读 polish_instruction 的本地缺口；再定位 existing_episode 最后一场最后 8-12 行；"
1264:                 "最后只围绕短对白补足、OS 后动作承接、最后两行追更断点做最小改动。"
1265:                 "润色前必须核对本集 C0/C1：能增强镜头和短台词，不能改主角动机、主动方、因果顺序、关键决定时机或证据来源。"
```
### Lines 1290-1385
```
1290:         ),
1291:     )
1292: 
1293: 
1294: def quality_user(
1295:     source_analysis: BaseModel,
1296:     episode_context: BaseModel,
1297:     story_bible: BaseModel,
1298:     script_batch: BaseModel,
1299:     previous_context: BaseModel | None,
1300:     viral_asset_report: BaseModel | None = None,
1301:     series_structure_plan: BaseModel | None = None,
1302:     episode_plan: BaseModel | None = None,
1303:     methodology_context: MethodologyContext | None = None,
1304: ) -> str:
1305:     return prompt_block(
1306:         dump_model("source_analysis", source_analysis),
1307:         dump_model("viral_asset_report", viral_asset_report),
1308:         dump_model("episode_context", episode_context),
1309:         dump_model("story_bible", story_bible),
1310:         dump_model("series_structure_plan", series_structure_plan),
1311:         dump_model("episode_plan", episode_plan),
1312:         render_script_batch_digest("script_batch_digest", script_batch),
1313:         dump_model("previous_context", previous_context),
1314:         section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
1315:         section("内部方法论", render_methodology_context(methodology_context)),
1316:         stage_instruction(
1317:             "检查 script_batch 是否达到可交付短剧正片标准。只要出现任一硬伤，status=needs_rewrite，并在 rewrite_instruction 中逐集说明怎么补足。",
1318:             (
1319:                 "本地确定性质检已经负责逐行硬指标：字数、行数、scene 数、action/dialogue 数量、"
1320:                 "action 格式、景别运镜、对白长度、最后两行模板和 metadata 泄漏。"
1321:                 "不要凭摘要声称逐行检查了每条 action 或每句对白，也不要把这些硬指标当成你的主要评分依据。"
1322:             ),
1323:             (
1324:                 "只基于 script_batch_digest 可见内容判断：戏剧质量、跨集连续性、人物动机、"
1325:                 "原著保真和题材模板一致性。重点看 opening_lines/tail_lines/scene_skeleton 是否显示"
1326:                 "冲突递进、信息增量、真实人物反应、原文 C0/C1 资产和可理解的关系状态。"
1327:                 "rewrite_instruction 必须指出第几集、哪个戏剧硬伤、回到哪条原文资产或哪段人物逻辑补救。"
1328:                 f"{SOURCE_FIDELITY_QUALITY_RULE}"
1329:             ),
1330:             (
1331:                 "如果 series_structure_plan 不为空，还要检查每集是否有信息增量、是否匹配对应 ending_hook_type、"
1332:                 "是否连续水集、是否偏离人物标签和全局节奏。"
1333:                 "cliffhanger 字段必须能在摘要中的 tail_lines 里找到可见承接；"
1334:                 "“留下悬念/关于身份的悬念/气氛紧张”等说明句不合格。"
1335:                 "必须检查第一场：原文有 C1 天然钩子但脚本删除/降级，或原文无天然钩子但脚本没有事实兼容型钩子，都不合格。"
1336:                 "必须检查人物：台词或动作若改变 Story Bible 中的人物动机、说话方式、关系状态，或把 C0 决策时机改掉，都不合格。"
1337:                 "如果摘要显示台词在解释价值观、同一情绪反复打转、上一集结尾和下一集开头不照应，必须指出。"
1338:             ),
1339:             (
1340:                 "如果用户可见剧本文本里把 hook/主情绪/watch_reason 当成独立说明展示，"
1341:                 "或出现“消费理由/观众要看/本集看点”等分析词，或摘要显示动作只是"
1342:                 "“众人震惊/气氛凝固/他很害怕”这种抽象描述，或对白显著啰嗦，也必须重写。"
1343:                 "题材模板错配必须拦截：男频穿越/大宋/武大郎/金莲/西门庆类不得混入"
1344:                 "真假千金/豪门宴会/总裁/亲子鉴定/大小姐模板，反向也不得串戏。"
1345:             ),
1346:         ),
1347:     )
1348: 
1349: 
1350: def state_user(
1351:     source_analysis: BaseModel,
1352:     episode_context: BaseModel,
1353:     story_bible: BaseModel,
1354:     script_batch: BaseModel,
1355:     quality_report: BaseModel,
1356:     previous_context: BaseModel | None,
1357:     episode_plan: BaseModel | None = None,
1358:     viral_asset_report: BaseModel | None = None,
1359:     series_structure_plan: BaseModel | None = None,
1360: ) -> str:
1361:     return prompt_block(
1362:         dump_model("source_analysis", source_analysis),
1363:         dump_model("viral_asset_report", viral_asset_report),
1364:         dump_model("episode_context", episode_context),
1365:         dump_model("story_bible", story_bible),
1366:         dump_model("series_structure_plan", series_structure_plan),
1367:         dump_model("episode_plan", episode_plan),
1368:         render_script_batch_digest("script_batch_digest", script_batch),
1369:         dump_model("quality_report", quality_report),
1370:         dump_model("previous_context", previous_context),
1371:         section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
1372:         stage_instruction(
1373:             "生成 next_round_context，保留 open_hooks、forbidden_reveals、character_knowledge、relationship_changes、prop_states、foreshadowing_ledger。",
1374:             (
1375:                 "先从 script_batch 最后一集向前回看本轮实际演出事实；再分离观众、主角、反派的知识层；"
1376:                 "随后记录关系变化、道具/证据状态、已埋/已回收伏笔；最后输出下一轮必须承接的 open_hooks 和 forbidden_reveals。"
1377:             ),
1378:             (
1379:                 "只回写 script_batch 中已经拍出来、说出来、露出来或被角色明确发现的内容；"
1380:                 "不得改写 story_bible，不得把新设定塞回 Bible，不得把未演出的小说原文当成本轮事实。"
1381:                 "character_knowledge 必须至少按 audience_known（观众已知）、protagonist_known（主角已知）、"
1382:                 "villain_known（反派已知）三类记录；每条写明谁知道什么、何时知道、哪些人仍不知道，用来维持信息差。"
1383:             ),
1384:             (
1385:                 "open_hooks 必须来自剧中实际演出的悬念，例如最后两行的威胁、动作未完成、"
```

## File: `src/novel_drama_engine/source_packets.py`
### Lines 1-140
```
1: from __future__ import annotations
2: 
3: import os
4: import re
5: from collections.abc import Iterable
6: 
7: from novel_drama_engine.models import (
8:     EpisodeContext,
9:     EpisodeDramaPlan,
10:     EpisodeHandoff,
11:     EpisodeScript,
12:     EpisodeSourceMapping,
13:     EpisodeSourcePacket,
14:     EpisodeSourcePackets,
15:     SeriesEpisodeOutline,
16:     SeriesStructurePlan,
17:     EpisodePlan,
18:     StoryBible,
19: )
20: 
21: 
22: DEFAULT_EXCERPT_CHARS = 12000
23: FORBIDDEN_RULE_NOISE = (
24:     "不得",
25:     "不能",
26:     "禁止",
27:     "不要",
28:     "新增",
29:     "加入",
30:     "添加",
31:     "改成",
32:     "提前",
33:     "泄露",
34:     "公开",
35: )
36: 
37: 
38: def _max_excerpt_chars() -> int:
39:     raw = os.environ.get("NOVEL_DRAMA_SOURCE_PACKET_CHARS", str(DEFAULT_EXCERPT_CHARS))
40:     try:
41:         return max(2000, int(raw))
42:     except ValueError:
43:         return DEFAULT_EXCERPT_CHARS
44: 
45: 
46: def _episode_numbers_from_range(target_episode_range: str) -> list[int]:
47:     match = re.fullmatch(r"EP(\d+)(?:-EP(\d+))?", target_episode_range.strip())
48:     if not match:
49:         return []
50:     start = int(match.group(1))
51:     end = int(match.group(2) or match.group(1))
52:     if end < start:
53:         return []
54:     return list(range(start, end + 1))
55: 
56: 
57: def _target_episode_number(value: str | int | None) -> int | None:
58:     if isinstance(value, int):
59:         return value
60:     if not isinstance(value, str):
61:         return None
62:     match = re.search(r"(?:EP|E|第)?\s*0*(\d{1,3})\s*(?:集)?", value, re.IGNORECASE)
63:     if not match:
64:         return None
65:     return int(match.group(1))
66: 
67: 
68: def _split_assets(value: list[str] | str | None) -> list[str]:
69:     if value is None:
70:         return []
71:     if isinstance(value, list):
72:         return [str(item).strip() for item in value if str(item).strip()]
73:     return [
74:         item.strip()
75:         for item in re.split(r"[、,，;；\n]", value)
76:         if item.strip()
77:     ]
78: 
79: 
80: def _dedupe(items: Iterable[str]) -> list[str]:
81:     seen: set[str] = set()
82:     result: list[str] = []
83:     for item in items:
84:         normalized = " ".join(str(item).split())
85:         if not normalized or normalized in seen:
86:             continue
87:         seen.add(normalized)
88:         result.append(normalized)
89:     return result
90: 
91: 
92: def _normalize_for_match(value: str) -> str:
93:     return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).lower()
94: 
95: 
96: GENERIC_CJK_TERMS = {
97:     "当前",
98:     "原文",
99:     "动作",
100:     "场面",
101:     "调度",
102:     "保留",
103:     "使用",
104:     "只用",
105:     "本集",
106:     "可见",
107:     "事件",
108:     "不要",
109:     "不得",
110:     "不能",
111:     "禁止",
112:     "提前",
113:     "新增",
114:     "改成",
115:     "成为",
116:     "通过",
117:     "结果",
118:     "观众",
119:     "以为",
120: }
121: 
122: 
123: def _cjk_terms(value: str) -> list[str]:
124:     terms: set[str] = set()
125:     for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", value):
126:         if len(chunk) >= 4 and chunk not in GENERIC_CJK_TERMS:
127:             terms.add(chunk)
128:         max_size = min(4, len(chunk))
129:         for size in range(2, max_size + 1):
130:             for index in range(0, len(chunk) - size + 1):
131:                 term = chunk[index : index + size]
132:                 if term in GENERIC_CJK_TERMS:
133:                     continue
134:                 terms.add(term)
135:     return sorted(terms, key=lambda item: (-len(item), item))
136: 
137: 
138: def _supported_by_excerpt(asset: str, source_excerpt: str) -> bool:
139:     normalized_asset = _normalize_for_match(asset)
140:     if len(normalized_asset) < 2:
```
### Lines 300-520
```
300:     right = min(len(source_text), end + padding)
301:     return _compact(source_text[left:right], max_chars)
302: 
303: 
304: def _find_asset_window(
305:     source_text: str,
306:     assets: list[str],
307:     max_chars: int,
308: ) -> str | None:
309:     positions: list[tuple[int, int]] = []
310:     for asset in assets:
311:         candidate = asset.strip()
312:         if len(candidate) < 4:
313:             continue
314:         found = source_text.find(candidate)
315:         if found >= 0:
316:             positions.append((found, found + len(candidate)))
317:     if not positions:
318:         return None
319:     return _window(source_text, min(pos[0] for pos in positions), max(pos[1] for pos in positions), max_chars)
320: 
321: 
322: def _proportional_excerpt(
323:     source_text: str,
324:     *,
325:     episode: int,
326:     target_episode_count: int | None,
327:     fallback_episode_count: int,
328:     max_chars: int,
329: ) -> str:
330:     total_episodes = max(target_episode_count or fallback_episode_count, episode, 1)
331:     length = len(source_text)
332:     start = int(length * (episode - 1) / total_episodes)
333:     end = int(length * episode / total_episodes)
334:     overlap = min(1200, max_chars // 5)
335:     return _compact(source_text[max(0, start - overlap) : min(length, end + overlap)], max_chars)
336: 
337: 
338: def _mapping_for_episode(
339:     mappings: list[EpisodeSourceMapping],
340:     episode: int,
341: ) -> EpisodeSourceMapping | None:
342:     explicit = [
343:         mapping
344:         for mapping in mappings
345:         if _target_episode_number(mapping.target_episode) == episode
346:     ]
347:     if explicit:
348:         return explicit[0]
349:     for mapping in mappings:
350:         if re.search(rf"\bEP\s*0*{episode}\b|第\s*{episode}\s*集", mapping.source, re.IGNORECASE):
351:             return mapping
352:     return None
353: 
354: 
355: def _normalized_contract_text(text: str) -> str:
356:     normalized = re.sub(r"\s+", "", text.strip())
357:     for token in FORBIDDEN_RULE_NOISE:
358:         normalized = normalized.replace(token, "")
359:     return re.sub(r"[，。、“”‘’：:；;,.!?！？\-—_（）()《》<>]", "", normalized)
360: 
361: 
362: def _source_packet_required_assets(
363:     episode_source_packets: EpisodeSourcePackets,
364: ) -> list[str]:
365:     assets: list[str] = []
366:     for packet in episode_source_packets.packets:
367:         assets.extend(
368:             [
369:                 *packet.c1_must_keep_assets,
370:                 *packet.c2_visual_assets,
371:                 *packet.golden_lines,
372:             ]
373:         )
374:     return list(dict.fromkeys(asset.strip() for asset in assets if asset.strip()))
375: 
376: 
377: def _rule_overlaps_required_asset(rule: str, required_assets: list[str]) -> bool:
378:     normalized_rule = _normalized_contract_text(rule)
379:     if len(normalized_rule) < 2:
380:         return False
381:     for asset in required_assets:
382:         normalized_asset = _normalized_contract_text(asset)
383:         if len(normalized_asset) < 2:
384:             continue
385:         if normalized_asset in normalized_rule or normalized_rule in normalized_asset:
386:             return True
387:     return False
388: 
389: 
390: def story_bible_source_packet_conflicts(
391:     story_bible: StoryBible,
392:     episode_source_packets: EpisodeSourcePackets,
393: ) -> list[str]:
394:     required_assets = _source_packet_required_assets(episode_source_packets)
395:     return [
396:         rule
397:         for rule in story_bible.forbidden_changes
398:         if _rule_overlaps_required_asset(rule, required_assets)
399:     ]
400: 
401: 
402: def normalize_story_bible_against_source_packets(
403:     story_bible: StoryBible,
404:     episode_source_packets: EpisodeSourcePackets,
405: ) -> StoryBible:
406:     conflicts = set(
407:         story_bible_source_packet_conflicts(story_bible, episode_source_packets)
408:     )
409:     if not conflicts:
410:         return story_bible
411:     return story_bible.model_copy(
412:         update={
413:             "forbidden_changes": [
414:                 rule for rule in story_bible.forbidden_changes if rule not in conflicts
415:             ]
416:         }
417:     )
418: 
419: 
420: def _outline_for_episode(
421:     series_structure_plan: SeriesStructurePlan | None,
422:     episode: int,
423: ) -> SeriesEpisodeOutline | None:
424:     if series_structure_plan is None:
425:         return None
426:     return next(
427:         (outline for outline in series_structure_plan.episode_outlines if outline.episode == episode),
428:         None,
429:     )
430: 
431: 
432: def _plan_for_episode(
433:     episode_plan: EpisodePlan | None,
434:     episode: int,
435: ) -> EpisodeDramaPlan | None:
436:     if episode_plan is None:
437:         return None
438:     return next((plan for plan in episode_plan.episodes if plan.episode == episode), None)
439: 
440: 
441: def build_episode_source_packets(
442:     *,
443:     source_text: str,
444:     episode_context: EpisodeContext,
445:     episode_plan: EpisodePlan | None = None,
446:     series_structure_plan: SeriesStructurePlan | None = None,
447:     target_episode_count: int | None = None,
448: ) -> EpisodeSourcePackets:
449:     episode_numbers = _episode_numbers_from_range(episode_context.target_episode_range)
450:     if not episode_numbers:
451:         episode_numbers = list(range(1, 2))
452:     max_chars = _max_excerpt_chars()
453:     heading_sections = _heading_sections(source_text)
454:     fallback_count = len(episode_numbers)
455:     packets: list[EpisodeSourcePacket] = []
456:     seen_fallback_required_assets: set[str] = set()
457: 
458:     for episode in episode_numbers:
459:         mapping = _mapping_for_episode(episode_context.source_to_episode_mapping, episode)
460:         outline = _outline_for_episode(series_structure_plan, episode)
461:         retained_assets = _split_assets(mapping.retained_assets if mapping else None)
462:         c1_assets = _dedupe(retained_assets)
463:         requested_source_anchor = (
464:             (outline.source_anchor if outline else "")
465:             or (mapping.source if mapping else "")
466:             or f"EP{episode:02d}"
467:         )
468: 
469:         if episode in heading_sections:
470:             start, end = heading_sections[episode]
471:             source_excerpt = _compact(source_text[start:end], max_chars)
472:         else:
473:             source_excerpt = _find_asset_window(
474:                 source_text,
475:                 [requested_source_anchor, *(c1_assets or [])],
476:                 max_chars,
477:             ) or _proportional_excerpt(
478:                 source_text,
479:                 episode=episode,
480:                 target_episode_count=target_episode_count
481:                 or series_structure_plan.target_episode_count
482:                 if series_structure_plan
483:                 else target_episode_count,
484:                 fallback_episode_count=fallback_count,
485:                 max_chars=max_chars,
486:             )
487: 
488:         source_anchor = (
489:             requested_source_anchor
490:             if _supported_by_excerpt(requested_source_anchor, source_excerpt)
491:             else f"EP{episode:02d} 当前集原文"
492:         )
493:         filtered_c1_assets = _filter_excerpt_assets(c1_assets, source_excerpt)
494:         source_window_is_reliable = episode in heading_sections or len(
495:             _normalize_for_match(source_excerpt)
496:         ) >= 80
497:         grounded_c1_assets = (
498:             _fill_with_source_grounded_items(
499:                 filtered_c1_assets,
500:                 packet=EpisodeSourcePacket(
501:                     episode=episode,
502:                     source_anchor=source_anchor,
503:                     source_excerpt=source_excerpt,
504:                 ),
505:                 min_length=1,
506:                 label="当前集原文必留",
507:             )
508:             if filtered_c1_assets or source_window_is_reliable
509:             else []
510:         )
511:         if not filtered_c1_assets:
512:             unique_fallback_c1_assets: list[str] = []
513:             for asset in grounded_c1_assets:
514:                 normalized_asset = _normalize_for_match(asset)
515:                 if normalized_asset in seen_fallback_required_assets:
516:                     continue
517:                 seen_fallback_required_assets.add(normalized_asset)
518:                 unique_fallback_c1_assets.append(asset)
519:             grounded_c1_assets = unique_fallback_c1_assets
520:         grounded_c0_facts = _fill_with_source_grounded_items(
```

## File: `src/novel_drama_engine/adaptation_quality.py`
### Lines 285-345
```
285: def _target_episode_number(value: str | int | None) -> int | None:
286:     if isinstance(value, int):
287:         return value
288:     if not isinstance(value, str):
289:         return None
290:     match = re.search(r"(?:EP|第)?\s*0*(\d{1,3})", value, flags=re.IGNORECASE)
291:     if not match:
292:         return None
293:     return int(match.group(1))
294: 
295: 
296: def _mapping_assets(mapping: object) -> list[tuple[int | None, str]]:
297:     if isinstance(mapping, str):
298:         return [(None, mapping)]
299:     if not hasattr(mapping, "model_dump"):
300:         return []
301:     data = mapping.model_dump()
302:     episode_number = _target_episode_number(data.get("target_episode"))
303:     assets: list[str] = []
304:     for key in ["source", "information_increment", "adaptation_action"]:
305:         value = data.get(key)
306:         if isinstance(value, str) and value.strip():
307:             assets.append(value.strip())
308:     retained_assets = data.get("retained_assets")
309:     if isinstance(retained_assets, str):
310:         assets.extend(asset.strip() for asset in re.split(r"[、,，;；]", retained_assets) if asset.strip())
311:     elif isinstance(retained_assets, list):
312:         assets.extend(str(asset).strip() for asset in retained_assets if str(asset).strip())
313:     return [(episode_number, asset) for asset in assets if asset]
314: 
315: 
316: def _mapping_required_assets(mapping: object) -> list[tuple[int | None, str]]:
317:     if isinstance(mapping, str):
318:         # Legacy string mappings are usually observational outlines such as
319:         # "A -> EP01"; keep them out of hard source fidelity scoring.
320:         return []
321:     if not hasattr(mapping, "model_dump"):
322:         return []
323:     data = mapping.model_dump()
324:     episode_number = _target_episode_number(data.get("target_episode"))
325:     retained_assets = data.get("retained_assets")
326:     assets: list[str] = []
327:     if isinstance(retained_assets, str):
328:         assets.extend(asset.strip() for asset in re.split(r"[、,，;；]", retained_assets) if asset.strip())
329:     elif isinstance(retained_assets, list):
330:         assets.extend(str(asset).strip() for asset in retained_assets if str(asset).strip())
331:     return [(episode_number, asset) for asset in assets if asset]
332: 
333: 
334: def _mapping_context_assets(mapping: object) -> list[tuple[int | None, str]]:
335:     if isinstance(mapping, str):
336:         return [(None, mapping)]
337:     if not hasattr(mapping, "model_dump"):
338:         return []
339:     data = mapping.model_dump()
340:     episode_number = _target_episode_number(data.get("target_episode"))
341:     assets: list[str] = []
342:     for key in ["source", "information_increment"]:
343:         value = data.get(key)
344:         if isinstance(value, str) and value.strip():
345:             assets.append(value.strip())
```
### Lines 770-1090
```
770:         advisory.append("story event ledger found no high-impact event markers")
771:     return entries, blocking, advisory
772: 
773: 
774: def build_source_fidelity_report(
775:     *,
776:     source_text: str,
777:     source_analysis: SourceAnalysis,
778:     episode_context: EpisodeContext,
779:     story_bible: StoryBible,
780:     script_batch: ScriptBatch,
781:     viral_asset_report: ViralAssetReport | None = None,
782: ) -> SourceFidelityReport:
783:     del viral_asset_report
784:     checks: list[SourceFidelityCheck] = []
785:     blocking: list[str] = []
786:     advisory: list[str] = []
787:     script_text = _all_script_text(script_batch)
788:     episode_texts = _episode_texts(script_batch)
789:     rendered_episode_numbers = set(episode_texts)
790: 
791:     for fact in story_bible.immutable_facts[:8]:
792:         evidence = _evidence_for(script_text, fact)
793:         checks.append(
794:             SourceFidelityCheck(
795:                 category="C0_immutable_fact",
796:                 anchor=fact,
797:                 status="passed" if evidence else "advisory",
798:                 evidence=evidence,
799:                 warning=None if evidence else "immutable fact tracked but not directly surfaced in this round",
800:             )
801:         )
802: 
803:     required_asset_total = 0
804:     required_asset_hits = 0
805:     for episode_number, asset in [
806:         pair
807:         for mapping in episode_context.source_to_episode_mapping
808:         for pair in _mapping_required_assets(mapping)
809:     ]:
810:         if len(normalize_text(asset)) < 4:
811:             continue
812:         if episode_number is not None and episode_number not in rendered_episode_numbers:
813:             continue
814:         required_asset_total += 1
815:         target_text = episode_texts.get(episode_number, script_text) if episode_number else script_text
816:         if _loose_contains(target_text, asset):
817:             required_asset_hits += 1
818:             checks.append(
819:                 SourceFidelityCheck(
820:                     category="source_mapping_required",
821:                     anchor=asset,
822:                     episode=episode_number,
823:                     status="passed",
824:                     evidence=_evidence_for(target_text, asset),
825:                 )
826:             )
827:             continue
828:         warning = f"source anchor not evidenced in script: {asset[:80]}"
829:         is_generic_planning_anchor = "->" in asset and re.search(
830:             r"(上一轮|开场|起势|继续|承接|推进)",
831:             asset,
832:         )
833:         if is_generic_planning_anchor:
834:             advisory.append(warning)
835:             status = "advisory"
836:         else:
837:             blocking.append(warning)
838:             status = "blocking"
839:         checks.append(
840:             SourceFidelityCheck(
841:                 category="source_mapping_required",
842:                 anchor=asset,
843:                 episode=episode_number,
844:                 status=status,
845:                 warning=warning,
846:             )
847:         )
848: 
849:     for episode_number, asset in [
850:         pair
851:         for mapping in episode_context.source_to_episode_mapping
852:         for pair in _mapping_context_assets(mapping)
853:     ]:
854:         if len(normalize_text(asset)) < 4:
855:             continue
856:         if episode_number is not None and episode_number not in rendered_episode_numbers:
857:             continue
858:         target_text = episode_texts.get(episode_number, script_text) if episode_number else script_text
859:         if _loose_contains(target_text, asset):
860:             checks.append(
861:                 SourceFidelityCheck(
862:                     category="source_mapping_context",
863:                     anchor=asset,
864:                     episode=episode_number,
865:                     status="passed",
866:                     evidence=_evidence_for(target_text, asset),
867:                 )
868:             )
869:             continue
870:         checks.append(
871:             SourceFidelityCheck(
872:                 category="source_mapping_context",
873:                 anchor=asset,
874:                 episode=episode_number,
875:                 status="advisory",
876:                 warning=f"source context not directly evidenced in script: {asset[:80]}",
877:             )
878:         )
879: 
880:     visual_hits = 0
881:     for moment in source_analysis.visual_moments[:10]:
882:         if _loose_contains(script_text, moment):
883:             visual_hits += 1
884:             checks.append(
885:                 SourceFidelityCheck(
886:                     category="C2_visual_asset",
887:                     anchor=moment,
888:                     status="passed",
889:                     evidence=_evidence_for(script_text, moment),
890:                 )
891:             )
892:     if source_analysis.visual_moments and visual_hits == 0:
893:         warning = "no source visual moment is preserved in the visible script"
894:         advisory.append(warning)
895:         checks.append(
896:             SourceFidelityCheck(
897:                 category="C2_visual_asset",
898:                 anchor="; ".join(source_analysis.visual_moments[:3]),
899:                 status="advisory",
900:                 warning=warning,
901:             )
902:         )
903: 
904:     first_episode = script_batch.episodes[0] if script_batch.episodes else None
905:     first_opening = _opening_text(first_episode) if first_episode else ""
906:     original_hook_preserved = False
907:     for hook in source_analysis.candidate_hooks[:3]:
908:         if _loose_contains(first_opening, hook) or _loose_contains(script_text, hook):
909:             original_hook_preserved = True
910:             checks.append(
911:                 SourceFidelityCheck(
912:                     category="hook_preservation",
913:                     anchor=hook,
914:                     episode=first_episode.episode if first_episode else None,
915:                     status="passed",
916:                     evidence=_evidence_for(first_opening or script_text, hook),
917:                 )
918:             )
919:             break
920:     if source_analysis.candidate_hooks and not original_hook_preserved:
921:         warning = (
922:             "original strong hook appears dropped instead of being preserved or visibly upgraded"
923:         )
924:         blocking.append(warning)
925:         checks.append(
926:             SourceFidelityCheck(
927:                 category="hook_preservation",
928:                 anchor="; ".join(source_analysis.candidate_hooks[:3]),
929:                 episode=first_episode.episode if first_episode else None,
930:                 status="blocking",
931:                 warning=warning,
932:             )
933:         )
934: 
935:     source_opening = source_text[:1600]
936:     if (
937:         first_episode is not None
938:         and OPENING_TENSION_SOURCE_RE.search(source_opening)
939:         and not OPENING_TENSION_SCRIPT_RE.search(first_opening)
940:     ):
941:         warning = (
942:             "source opening tension asset was removed instead of being safely visualized"
943:         )
944:         blocking.append(warning)
945:         checks.append(
946:             SourceFidelityCheck(
947:                 category="opening_tension_preservation",
948:                 anchor=source_opening[:160],
949:                 episode=first_episode.episode,
950:                 status="blocking",
951:                 warning=warning,
952:             )
953:         )
954: 
955:     for warning in _detect_intent_drift(source_text, script_text):
956:         blocking.append(warning)
957:         checks.append(
958:             SourceFidelityCheck(
959:                 category="intent_drift",
960:                 anchor=warning,
961:                 status="blocking",
962:                 warning=warning,
963:             )
964:         )
965: 
966:     for warning in _detect_agency_ramp_drift(
967:         source_text=source_text,
968:         episode_context=episode_context,
969:         script_batch=script_batch,
970:     ):
971:         blocking.append(warning)
972:         checks.append(
973:             SourceFidelityCheck(
974:                 category="agency_ramp",
975:                 anchor=source_text[:160],
976:                 status="blocking",
977:                 evidence=_evidence_for(_early_script_text(script_batch), "早就知道"),
978:                 warning=warning,
979:             )
980:         )
981: 
982:     for warning in _detect_support_takeover(script_text):
983:         blocking.append(warning)
984:         checks.append(
985:             SourceFidelityCheck(
986:                 category="support_role_boundary",
987:                 anchor="support_role_agency_boundary",
988:                 status="blocking",
989:                 warning=warning,
990:             )
991:         )
992: 
993:     for warning in _detect_opponent_passivity(
994:         source_analysis=source_analysis,
995:         story_bible=story_bible,
996:         script_text=script_text,
997:     ):
998:         blocking.append(warning)
999:         checks.append(
1000:             SourceFidelityCheck(
1001:                 category="opponent_agency",
1002:                 anchor="opponent_active_countermove",
1003:                 status="blocking",
1004:                 warning=warning,
1005:             )
1006:         )
1007: 
1008:     for rule in story_bible.forbidden_changes:
1009:         if _forbidden_change_leaked(script_text, rule):
1010:             warning = f"forbidden addition/reveal may have leaked into script: {rule}"
1011:             blocking.append(warning)
1012:             checks.append(
1013:                 SourceFidelityCheck(
1014:                     category="C4_forbidden_addition",
1015:                     anchor=rule,
1016:                     status="blocking",
1017:                     evidence=_evidence_for(script_text, _forbidden_term(rule)),
1018:                     warning=warning,
1019:                 )
1020:             )
1021: 
1022:     for rule in episode_context.forbidden_reveals:
1023:         term = _forbidden_term(rule)
1024:         if len(normalize_text(term)) < 2:
1025:             continue
1026:         if _forbidden_rule_leaked(script_text, rule):
1027:             warning = f"forbidden addition/reveal may have leaked into script: {rule}"
1028:             blocking.append(warning)
1029:             checks.append(
1030:                 SourceFidelityCheck(
1031:                     category="C4_forbidden_addition",
1032:                     anchor=rule,
1033:                     status="blocking",
1034:                     evidence=_evidence_for(script_text, term),
1035:                     warning=warning,
1036:                 )
1037:             )
1038: 
1039:     known_names = set(source_analysis.characters) | set(story_bible.characters)
1040:     unknown_names = sorted(
1041:         name
1042:         for name in _script_characters(script_batch)
1043:         if not _known_character_match(name, known_names)
1044:     )
1045:     if len(unknown_names) >= 4:
1046:         warning = "新增多个未追踪说话角色，疑似替模型补剧情：" + "、".join(unknown_names[:6])
1047:         advisory.append(warning)
1048:         checks.append(
1049:             SourceFidelityCheck(
1050:                 category="character_integrity",
1051:                 anchor="、".join(unknown_names[:6]),
1052:                 status="advisory",
1053:                 warning=warning,
1054:             )
1055:         )
1056: 
1057:     if source_text and not any(_loose_contains(script_text, token) for token in _tokens(source_text)[:12]):
1058:         warning = "script has weak lexical overlap with the uploaded source"
1059:         advisory.append(warning)
1060:         checks.append(
1061:             SourceFidelityCheck(
1062:                 category="C1_must_keep_scene",
1063:                 anchor=source_text[:80],
1064:                 status="advisory",
1065:                 warning=warning,
1066:             )
1067:         )
1068: 
1069:     asset_score = (
1070:         round((required_asset_hits / required_asset_total) * 100)
1071:         if required_asset_total
1072:         else 100
1073:     )
1074:     non_asset_blockers = [
1075:         warning
1076:         for warning in blocking
1077:         if not warning.startswith("source anchor not evidenced in script:")
1078:     ]
1079:     penalty_score = max(0, 100 - len(non_asset_blockers) * 18 - len(advisory) * 4)
1080:     score = min(asset_score, penalty_score)
1081:     return SourceFidelityReport(
1082:         score=score,
1083:         preserved_original_hook=original_hook_preserved,
1084:         checks=checks,
1085:         blocking_warnings=blocking,
1086:         advisory_warnings=advisory,
1087:     )
1088: 
1089: 
1090: def _tail_text(episode: EpisodeScript, line_count: int = 4) -> str:
```
### Lines 1360-1585
```
1360:         warnings=warnings,
1361:     )
1362: 
1363: 
1364: def build_adaptation_quality_report(
1365:     *,
1366:     source_text: str,
1367:     source_analysis: SourceAnalysis,
1368:     episode_context: EpisodeContext,
1369:     story_bible: StoryBible,
1370:     script_batch: ScriptBatch,
1371:     next_round_context: NextRoundContext,
1372:     previous_context: NextRoundContext | None,
1373:     viral_asset_report: ViralAssetReport | None = None,
1374:     episode_plan: EpisodePlan | None = None,
1375:     series_structure_plan: SeriesStructurePlan | None = None,
1376: ) -> AdaptationQualityReport:
1377:     source_fidelity = build_source_fidelity_report(
1378:         source_text=source_text,
1379:         source_analysis=source_analysis,
1380:         episode_context=episode_context,
1381:         story_bible=story_bible,
1382:         script_batch=script_batch,
1383:         viral_asset_report=viral_asset_report,
1384:     )
1385:     continuity = build_continuity_audit_report(
1386:         episode_context=episode_context,
1387:         script_batch=script_batch,
1388:         previous_context=previous_context,
1389:     )
1390:     ledger = build_story_state_ledger(
1391:         script_batch=script_batch,
1392:         next_round_context=next_round_context,
1393:         previous_context=previous_context,
1394:         episode_context=episode_context,
1395:         episode_plan=episode_plan,
1396:         series_structure_plan=series_structure_plan,
1397:     )
1398:     blocking = dedupe_quality_items([
1399:         *source_fidelity.blocking_warnings,
1400:         *continuity.blocking_warnings,
1401:         *ledger.blocking_warnings,
1402:     ])
1403:     advisory = dedupe_quality_items([
1404:         *source_fidelity.advisory_warnings,
1405:         *continuity.advisory_warnings,
1406:         *ledger.warnings,
1407:     ])
1408:     rewrite_instruction = ""
1409:     if blocking:
1410:         rewrite_instruction = (
1411:             "改编一致性阻断：必须保留原著强钩子/名场面/主动方逻辑，不得泄露 forbidden reveal，"
1412:             "不得新增 story bible 禁止项；必须遵守故事事件账本，同一高价值名场面不得重复兑现，"
1413:             "身份/机构/舆论/权威裁决类结果必须先交代证据来源和流程；"
1414:             "必须守住主角情绪递进、支持角色选择权边界和对手主动反制。具体问题："
1415:             + "；".join(blocking[:6])
1416:         )
1417:     return AdaptationQualityReport(
1418:         source_fidelity=source_fidelity,
1419:         continuity=continuity,
1420:         story_state_ledger=ledger,
1421:         blocking_warnings=blocking,
1422:         advisory_warnings=advisory,
1423:         rewrite_instruction=rewrite_instruction,
1424:     )
1425: 
1426: 
1427: def build_methodology_quality_report(
1428:     *,
1429:     source_analysis: SourceAnalysis,
1430:     script_batch: ScriptBatch,
1431:     source_strength_profile: SourceStrengthProfile,
1432:     methodology_context: MethodologyContext | None,
1433:     viral_asset_report: ViralAssetReport | None = None,
1434: ) -> MethodologyQualityReport:
1435:     if (
1436:         source_strength_profile.overall_level != SourceStrengthLevel.STRONG
1437:         or source_strength_profile.recommended_intensity != AdaptationIntensity.LIGHT
1438:         or methodology_context is None
1439:     ):
1440:         return MethodologyQualityReport()
1441: 
1442:     source_fidelity_cards = [
1443:         card
1444:         for card in methodology_context.cards
1445:         if card.category == "source_fidelity"
1446:     ]
1447:     if not source_fidelity_cards:
1448:         return MethodologyQualityReport()
1449: 
1450:     card = source_fidelity_cards[0]
1451:     script_text = _all_script_text(script_batch)
1452:     first_episode = script_batch.episodes[0] if script_batch.episodes else None
1453:     is_opening_round = first_episode is None or first_episode.episode <= 1
1454:     first_opening = _opening_text(first_episode) if first_episode else ""
1455:     issues: list[MethodologyQualityIssue] = []
1456: 
1457:     if is_opening_round:
1458:         for hook in source_analysis.candidate_hooks[:3]:
1459:             if not hook.strip():
1460:                 continue
1461:             if _loose_contains(first_opening, hook) or _loose_contains(script_text, hook):
1462:                 continue
1463:             issues.append(
1464:                 MethodologyQualityIssue(
1465:                     card_id=card.id,
1466:                     card_name=card.name,
1467:                     severity="blocking",
1468:                     episode=first_episode.episode if first_episode else None,
1469:                     message=f"强原文轻改失败：原文开场钩子未被保留或视听化：{hook}",
1470:                     evidence=_evidence_for(script_text, hook),
1471:                 )
1472:             )
1473: 
1474:         high_value_assets = list(source_analysis.visual_moments[:8])
1475:         if viral_asset_report is not None:
1476:             high_value_assets.extend(viral_asset_report.signature_scenes[:5])
1477:         high_value_assets = list(
1478:             dict.fromkeys(asset for asset in high_value_assets if asset.strip())
1479:         )
1480:         if high_value_assets and not any(
1481:             _loose_contains(script_text, asset) for asset in high_value_assets
1482:         ):
1483:             issues.append(
1484:                 MethodologyQualityIssue(
1485:                     card_id=card.id,
1486:                     card_name=card.name,
1487:                     severity="blocking",
1488:                     episode=first_episode.episode if first_episode else None,
1489:                     message=(
1490:                         "强原文轻改失败：原文高价值画面/名场面没有在正片中被保留，"
1491:                         "不能只重构成泛化冲突。"
1492:                     ),
1493:                     evidence=high_value_assets[:4],
1494:                 )
1495:             )
1496: 
1497:     for negative_example in card.negative_examples[:5]:
1498:         if not negative_example.strip():
1499:             continue
1500:         if _loose_contains(script_text, negative_example):
1501:             issues.append(
1502:                 MethodologyQualityIssue(
1503:                     card_id=card.id,
1504:                     card_name=card.name,
1505:                     severity="blocking",
1506:                     episode=None,
1507:                     message=f"强原文轻改失败：脚本疑似命中方法论反例：{negative_example}",
1508:                     evidence=_evidence_for(script_text, negative_example),
1509:                 )
1510:             )
1511: 
1512:     rewrite_instruction = ""
1513:     if issues:
1514:         rewrite_instruction = (
1515:             "方法论阻断：本素材被判定为强原文，只允许轻改。必须回到原文 C0/C1："
1516:             "保留开场钩子、主动方、因果顺序、关键决定时机和名场面；"
1517:             "只做镜头视听化、短台词化、压缩和衔接补强。具体问题："
1518:             + "；".join(issue.message for issue in issues[:6])
1519:         )
1520:     return MethodologyQualityReport(issues=issues, rewrite_instruction=rewrite_instruction)
1521: 
1522: 
1523: def merge_methodology_quality_into_report(
1524:     report,
1525:     methodology_report: MethodologyQualityReport,
1526: ):
1527:     blocking_issues = dedupe_quality_items([
1528:         issue.message
1529:         for issue in methodology_report.issues
1530:         if issue.severity == "blocking"
1531:     ])
1532:     if not blocking_issues:
1533:         return report
1534: 
1535:     status = (
1536:         QualityStatus.NEEDS_REWRITE
1537:         if report.status == QualityStatus.USABLE
1538:         else report.status
1539:     )
1540:     rewrite_instruction = merge_rewrite_instructions(
1541:         [
1542:             methodology_report.rewrite_instruction,
1543:             report.rewrite_instruction,
1544:         ],
1545:         blocking=True,
1546:     )
1547:     return report.model_copy(
1548:         update={
1549:             "status": status,
1550:             "blocking_issues": dedupe_quality_items(
1551:                 [*report.blocking_issues, *blocking_issues]
1552:             ),
1553:             "rewrite_instruction": rewrite_instruction,
1554:         }
1555:     )
1556: 
1557: 
1558: def merge_adaptation_quality_into_report(
1559:     report,
1560:     adaptation_report: AdaptationQualityReport,
1561: ):
1562:     if not adaptation_report.blocking_warnings:
1563:         return report
1564: 
1565:     blocking_issues = dedupe_quality_items([
1566:         *report.blocking_issues,
1567:         *adaptation_report.blocking_warnings,
1568:     ])
1569:     rewrite_instruction = merge_rewrite_instructions(
1570:         [
1571:             adaptation_report.rewrite_instruction,
1572:             report.rewrite_instruction,
1573:         ],
1574:         blocking=True,
1575:     )
1576:     status = (
1577:         QualityStatus.NEEDS_REWRITE
1578:         if report.status == QualityStatus.USABLE
1579:         else report.status
1580:     )
1581:     return report.model_copy(
1582:         update={
1583:             "status": status,
1584:             "blocking_issues": blocking_issues,
1585:             "rewrite_instruction": rewrite_instruction,
```

## File: `src/novel_drama_engine/source_evidence.py`
### Lines 1-405
```
1: from __future__ import annotations
2: 
3: import re
4: 
5: from novel_drama_engine.models import (
6:     EpisodeContext,
7:     EpisodeScript,
8:     EpisodeSourceMapping,
9:     EpisodeSourcePacket,
10:     EpisodeSourcePackets,
11:     QualityReport,
12:     QualityStatus,
13:     ScriptBatch,
14:     SourceEvidenceItem,
15:     SourceEvidenceReport,
16:     SourceEvidenceSpan,
17: )
18: from novel_drama_engine.quality_text import (
19:     dedupe_quality_items,
20:     merge_rewrite_instructions,
21: )
22: from novel_drama_engine.renderer import render_shooting_episode
23: 
24: 
25: def _compact(text: str) -> str:
26:     return re.sub(r"\s+", "", text.strip())
27: 
28: 
29: def _split_assets(value: list[str] | str | None) -> list[str]:
30:     if value is None:
31:         return []
32:     if isinstance(value, str):
33:         parts = re.split(r"[、,，；;|\n]+", value)
34:     else:
35:         parts = value
36:     ignored = {"none", "null", "nil", "-", "无", "暂无"}
37:     return [
38:         part.strip()
39:         for part in parts
40:         if part and part.strip() and part.strip().lower() not in ignored
41:     ]
42: 
43: 
44: def _asset_needles(asset: str) -> list[str]:
45:     compact = _compact(asset)
46:     if not compact:
47:         return []
48:     needles = [compact]
49:     cjk_runs = re.findall(r"[\u4e00-\u9fff]{3,}", compact)
50:     for run in cjk_runs:
51:         for size in (4, 3):
52:             for index in range(0, len(run) - size + 1):
53:                 needles.append(run[index : index + size])
54:     return list(dict.fromkeys(needles))
55: 
56: 
57: def _asset_tokens(asset: str) -> list[str]:
58:     compact = _compact(asset)
59:     tokens: list[str] = []
60:     for run in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", compact):
61:         tokens.append(run)
62:         if re.fullmatch(r"[\u4e00-\u9fff]{4,}", run):
63:             tokens.extend(run[index : index + 2] for index in range(0, len(run) - 1))
64:     return list(dict.fromkeys(token for token in tokens if len(token) >= 2))
65: 
66: 
67: def _has_specific_asset_overlap(line: str, asset: str) -> bool:
68:     compact_asset = _compact(asset)
69:     if len(compact_asset) <= 4:
70:         return False
71:     compact_line = _compact(line)
72:     late_tokens = _asset_tokens(compact_asset[4:])
73:     return any(token in compact_line for token in late_tokens)
74: 
75: 
76: def _line_matches_asset(line: str, asset: str) -> bool:
77:     compact_line = _compact(line)
78:     if not compact_line:
79:         return False
80:     compact_asset = _compact(asset)
81:     if compact_asset and compact_asset in compact_line:
82:         return True
83:     if len(compact_asset) <= 4:
84:         return any(needle in compact_line for needle in _asset_needles(asset))
85: 
86:     tokens = _asset_tokens(asset)
87:     if not tokens:
88:         return False
89:     matched = sum(1 for token in tokens if token in compact_line)
90:     coverage = matched / max(1, len(tokens))
91:     return matched >= 3 and coverage >= 0.25 and _has_specific_asset_overlap(line, asset)
92: 
93: 
94: def _asset_match_score(line: str, asset: str) -> float:
95:     compact_line = _compact(line)
96:     compact_asset = _compact(asset)
97:     if not compact_line:
98:         return 0
99:     if compact_asset and compact_asset in compact_line:
100:         return 1000 + len(compact_asset)
101:     tokens = _asset_tokens(asset)
102:     if not tokens:
103:         return 0
104:     matched = sum(1 for token in tokens if token in compact_line)
105:     coverage = matched / max(1, len(tokens))
106:     if not _line_matches_asset(line, asset):
107:         return 0
108:     late_bonus = 2 if _has_specific_asset_overlap(line, asset) else 0
109:     return matched + coverage + late_bonus
110: 
111: 
112: def _script_line_entries(script: EpisodeScript) -> list[tuple[int, str]]:
113:     rendered = render_shooting_episode(script)
114:     return [
115:         (index, line.strip())
116:         for index, line in enumerate(rendered.splitlines(), start=1)
117:         if line.strip()
118:     ]
119: 
120: 
121: def _script_lines(script: EpisodeScript) -> list[str]:
122:     return [line for _, line in _script_line_entries(script)]
123: 
124: 
125: def _line_entry_for_asset(
126:     entries: list[tuple[int, str]],
127:     asset: str,
128: ) -> tuple[int | None, str | None]:
129:     candidates = [
130:         (_asset_match_score(line, asset), index, line)
131:         for index, line in entries
132:     ]
133:     candidates = [candidate for candidate in candidates if candidate[0] > 0]
134:     if not candidates:
135:         return None, None
136:     _, index, line = max(candidates, key=lambda item: item[0])
137:     return index, line
138: 
139: 
140: def _source_line_for_asset(
141:     packet: EpisodeSourcePacket,
142:     asset: str,
143: ) -> tuple[int | None, str | None]:
144:     lines = [line.strip() for line in packet.source_excerpt.splitlines() if line.strip()]
145:     candidates = [
146:         (_asset_match_score(line, asset), index, line)
147:         for index, line in enumerate(lines, start=1)
148:     ]
149:     candidates = [candidate for candidate in candidates if candidate[0] > 0]
150:     if candidates:
151:         _, index, line = max(candidates, key=lambda item: item[0])
152:         return index, line
153:     anchor = packet.source_anchor.strip()
154:     if anchor and _line_matches_asset(anchor, asset):
155:         return 1, anchor
156:     return None, None
157: 
158: 
159: def _evidence_span_for_asset(
160:     packet: EpisodeSourcePacket,
161:     asset: str,
162:     script_entries: list[tuple[int, str]],
163:     adaptation_reason: str,
164: ) -> SourceEvidenceSpan:
165:     source_line_index, source_line = _source_line_for_asset(packet, asset)
166:     script_line_index, script_line = _line_entry_for_asset(script_entries, asset)
167:     return SourceEvidenceSpan(
168:         asset=asset,
169:         source_anchor=packet.source_anchor,
170:         source_excerpt=packet.source_excerpt,
171:         source_line=source_line,
172:         source_line_index=source_line_index,
173:         script_line=script_line,
174:         script_line_index=script_line_index,
175:         adaptation_reason=adaptation_reason,
176:         status="matched" if script_line else "missing",
177:     )
178: 
179: 
180: def _packet_assets(packet: EpisodeSourcePacket) -> list[str]:
181:     if packet.source_evidence_assets is not None:
182:         return _split_assets(packet.source_evidence_assets)
183:     return _split_assets(packet.c1_must_keep_assets)
184: 
185: 
186: def _is_system_placeholder_anchor(anchor: str) -> bool:
187:     return bool(
188:         re.fullmatch(
189:             r"EP\d{2,3}\s+当前集原文",
190:             anchor.strip(),
191:             flags=re.IGNORECASE,
192:         )
193:     )
194: 
195: 
196: def _packet_reason(packet: EpisodeSourcePacket) -> str:
197:     if packet.c1_must_keep_assets:
198:         return "保留原文必留资产：" + "、".join(packet.c1_must_keep_assets[:4])
199:     if packet.c0_facts:
200:         return "承接原文关键信息：" + "、".join(packet.c0_facts[:3])
201:     return "追踪原文锚点是否落到正片。"
202: 
203: 
204: def _episode_number_from_mapping(mapping: EpisodeSourceMapping) -> int | None:
205:     value = mapping.target_episode
206:     if isinstance(value, int):
207:         return value
208:     if isinstance(value, str):
209:         match = re.search(r"\d+", value)
210:         if match:
211:             return int(match.group(0))
212:     return None
213: 
214: 
215: def _mapping_packets(episode_context: EpisodeContext) -> list[EpisodeSourcePacket]:
216:     packets: list[EpisodeSourcePacket] = []
217:     fallback_episode = 1
218:     for mapping in episode_context.source_to_episode_mapping:
219:         episode = _episode_number_from_mapping(mapping) or fallback_episode
220:         fallback_episode = episode + 1
221:         retained_assets = _split_assets(mapping.retained_assets)
222:         packets.append(
223:             EpisodeSourcePacket(
224:                 episode=episode,
225:                 source_anchor=mapping.source,
226:                 source_excerpt=mapping.source,
227:                 c0_facts=_split_assets(mapping.information_increment),
228:                 c1_must_keep_assets=retained_assets,
229:                 c2_visual_assets=_split_assets(mapping.adaptation_action),
230:             )
231:         )
232:     return packets
233: 
234: 
235: def build_source_evidence_report(
236:     script_batch: ScriptBatch,
237:     *,
238:     episode_source_packets: EpisodeSourcePackets | None = None,
239:     episode_context: EpisodeContext | None = None,
240: ) -> SourceEvidenceReport:
241:     scripts = {script.episode: script for script in script_batch.episodes}
242:     packets = (
243:         episode_source_packets.packets
244:         if episode_source_packets is not None
245:         else _mapping_packets(episode_context)
246:         if episode_context is not None
247:         else []
248:     )
249: 
250:     items: list[SourceEvidenceItem] = []
251:     missing_items: list[str] = []
252:     matched_count = 0
253:     total_count = 0
254: 
255:     for packet in packets:
256:         script = scripts.get(packet.episode)
257:         if script is None:
258:             continue
259:         hard_assets = _packet_assets(packet)
260:         assets = hard_assets
261:         if not assets:
262:             assets = _split_assets(packet.c1_must_keep_assets)
263:         if not assets:
264:             assets = _split_assets(packet.c0_facts)
265:         if not assets and not _is_system_placeholder_anchor(packet.source_anchor):
266:             assets = [packet.source_anchor]
267: 
268:         adaptation_reason = _packet_reason(packet)
269:         line_entries = _script_line_entries(script) if script is not None else []
270:         evidence_spans = [
271:             _evidence_span_for_asset(
272:                 packet,
273:                 asset,
274:                 line_entries,
275:                 adaptation_reason,
276:             )
277:             for asset in assets
278:         ]
279: 
280:         total_count += len(evidence_spans)
281:         matched_spans = [span for span in evidence_spans if span.status == "matched"]
282:         missing_spans = [span for span in evidence_spans if span.status == "missing"]
283:         matched_count += len(matched_spans)
284:         script_evidence = [
285:             span.script_line for span in matched_spans if span.script_line
286:         ]
287:         unique_evidence = list(dict.fromkeys(script_evidence))[:6]
288:         if missing_spans and hard_assets:
289:             missing_items.extend(
290:                 f"EP{packet.episode:02d} 缺少原文资产：{span.asset}"
291:                 for span in missing_spans
292:             )
293: 
294:         if matched_spans and missing_spans:
295:             status = "partial"
296:         elif matched_spans:
297:             status = "matched"
298:         else:
299:             status = "missing"
300: 
301:         items.append(
302:             SourceEvidenceItem(
303:                 episode=packet.episode,
304:                 source_anchor=packet.source_anchor,
305:                 adaptation_reason=adaptation_reason,
306:                 retained_assets=assets,
307:                 script_evidence=unique_evidence,
308:                 evidence_spans=evidence_spans,
309:                 status=status,
310:             )
311:         )
312: 
313:     coverage_score = round((matched_count / total_count) * 100) if total_count else 100
314:     rewrite_instruction = ""
315:     if missing_items:
316:         rewrite_instruction = (
317:             "原文证据未落到正片：请优先把缺失的必留资产转成可见动作、道具、"
318:             "关系反应或短对白；强原文本身已有爆款冲突时，只做视听化增强，不要另起新冲突。"
319:         )
320: 
321:     return SourceEvidenceReport(
322:         coverage_score=coverage_score,
323:         items=items,
324:         missing_items=missing_items,
325:         rewrite_instruction=rewrite_instruction,
326:     )
327: 
328: 
329: def merge_source_evidence_into_quality_report(
330:     quality_report: QualityReport,
331:     source_evidence_report: SourceEvidenceReport,
332: ) -> QualityReport:
333:     if not source_evidence_report.missing_items:
334:         return quality_report
335:     missing_preview = "；".join(source_evidence_report.missing_items[:5])
336:     blocking_issue = f"source_evidence: {missing_preview}"
337:     blocking_issues = dedupe_quality_items([*quality_report.blocking_issues, blocking_issue])
338:     rewrite_instruction = merge_rewrite_instructions(
339:         [
340:             quality_report.rewrite_instruction,
341:             source_evidence_report.rewrite_instruction,
342:             missing_preview,
343:         ],
344:         blocking=True,
345:     )
346:     return quality_report.model_copy(
347:         update={
348:             "status": QualityStatus.NEEDS_REWRITE,
349:             "blocking_issues": blocking_issues,
350:             "rewrite_instruction": rewrite_instruction,
351:         }
352:     )
353: 
354: 
355: def render_source_evidence_report(report: SourceEvidenceReport) -> str:
356:     parts = [
357:         "# Source Evidence Report",
358:         "",
359:         f"- Coverage: {report.coverage_score}%",
360:         f"- Missing: {len(report.missing_items)}",
361:     ]
362:     if report.rewrite_instruction:
363:         parts.extend(["", f"Rewrite: {report.rewrite_instruction}"])
364:     for item in report.items:
365:         parts.extend(
366:             [
367:                 "",
368:                 f"## EP{item.episode:02d} · {item.status}",
369:                 f"- Source: {item.source_anchor}",
370:                 f"- Reason: {item.adaptation_reason}",
371:                 f"- Assets: {'、'.join(item.retained_assets) if item.retained_assets else '-'}",
372:             ]
373:         )
374:         if item.script_evidence:
375:             parts.append("- Script Evidence:")
376:             parts.extend(f"  - {line}" for line in item.script_evidence)
377:         if item.evidence_spans:
378:             parts.append("- Source Span Evidence:")
379:             for span in item.evidence_spans:
380:                 source_ref = (
381:                     f"source L{span.source_line_index}: {span.source_line}"
382:                     if span.source_line_index and span.source_line
383:                     else "source missing"
384:                 )
385:                 script_ref = (
386:                     f"script L{span.script_line_index}: {span.script_line}"
387:                     if span.script_line_index and span.script_line
388:                     else "script missing"
389:                 )
390:                 parts.append(
391:                     f"  - {span.status} · {span.asset} · {source_ref} -> {script_ref}"
392:                 )
393:     if report.missing_items:
394:         parts.extend(["", "## Missing Items"])
395:         parts.extend(f"- {item}" for item in report.missing_items)
396:     return "\n".join(parts).strip() + "\n"
```

## File: `src/novel_drama_engine/drama_quality.py`
### Lines 180-395
```
180:         _dimension(
181:             "conflict_causality",
182:             conflict_score,
183:             evidence=[
184:                 f"avg_action_lines={avg_action_lines:.1f}",
185:                 f"avg_voiced_lines={avg_voiced_lines:.1f}",
186:             ],
187:             suggestion="补清楚谁主动做了什么、对手如何反制、当场后果是什么。",
188:         ),
189:         _dimension(
190:             "emotional_progression",
191:             emotion_score,
192:             evidence=[f"avg_emotion_turns={avg_emotion_turns:.1f}"],
193:             suggestion="补足震惊、克制、反击、失落或爽点的递进，不要一上来全知全能开杀。",
194:         ),
195:         _dimension(
196:             "dialogue_naturalness",
197:             dialogue_score,
198:             evidence=_dialogue_samples(script_batch),
199:             suggestion="删掉解释型长句，把信息藏进短对白、停顿、动作和潜台词。",
200:         ),
201:         _dimension(
202:             "hook_and_cliffhanger",
203:             hook_score,
204:             evidence=[warning for warning in warnings if "cliffhanger" in warning][:3],
205:             suggestion="把开场钩子和结尾钩子写成已经演出来的动作/道具/短台词。",
206:         ),
207:     ]
208:     return dimensions, warnings
209: 
210: 
211: def _source_asset_dimension(
212:     adaptation_quality_report: AdaptationQualityReport | None,
213: ) -> DramaQualityDimension:
214:     if adaptation_quality_report is None:
215:         return _dimension(
216:             "source_asset_preservation",
217:             7,
218:             evidence=["no adaptation_quality_report"],
219:             suggestion="需要结合原文 C0/C1 和 source fidelity report 复核。",
220:             blocking_at=4,
221:         )
222: 
223:     fidelity = adaptation_quality_report.source_fidelity
224:     score = round(fidelity.score / 10)
225:     evidence = [
226:         *fidelity.blocking_warnings[:2],
227:         *fidelity.advisory_warnings[:2],
228:     ]
229:     if fidelity.score < 50:
230:         evidence.insert(0, f"source similarity below 5/10: {fidelity.score}/100")
231:         score = min(score, 4)
232:     evidence_text = "\n".join(evidence)
233:     has_source_blocker = bool(fidelity.blocking_warnings) or any(
234:         token in evidence_text for token in SOURCE_FIDELITY_BLOCKING_WARNING_TOKENS
235:     )
236:     if has_source_blocker:
237:         score = min(score, 4)
238:     return _dimension(
239:         "source_asset_preservation",
240:         score,
241:         evidence=evidence,
242:         suggestion="恢复原文强冲突、关键情绪和不可改事实，避免为了爽点改掉核心逻辑。",
243:         blocking_at=4,
244:     )
245: 
246: 
247: def _overall(dimensions: list[DramaQualityDimension]) -> int:
248:     if not dimensions:
249:         return 0
250:     weights = Counter(
251:         {
252:             "character_integrity": 2,
253:             "conflict_causality": 2,
254:             "emotional_progression": 2,
255:             "dialogue_naturalness": 1,
256:             "source_asset_preservation": 2,
257:             "hook_and_cliffhanger": 1,
258:         }
259:     )
260:     weighted_total = sum(item.score * weights[item.name] for item in dimensions)
261:     total_weight = sum(weights[item.name] for item in dimensions)
262:     return _clamp(round(weighted_total / total_weight))
263: 
264: 
265: def _baseline_score(script_batch: ScriptBatch) -> int:
266:     dimensions, _ = _score_from_metrics(script_batch, None)
267:     dimensions.append(_dimension("source_asset_preservation", 7, blocking_at=4))
268:     return _overall(dimensions)
269: 
270: 
271: def _comparison(
272:     *,
273:     pipeline_score: int,
274:     baseline_script_batch: ScriptBatch | None,
275: ) -> DramaQualityComparison | None:
276:     if baseline_script_batch is None:
277:         return None
278:     baseline_score = _baseline_score(baseline_script_batch)
279:     delta = pipeline_score - baseline_score
280:     if delta >= 2:
281:         verdict = "pipeline_clearly_better"
282:         reason = "pipeline overall score is at least 2 points above the direct baseline."
283:     elif delta == 1:
284:         verdict = "pipeline_slightly_better"
285:         reason = "pipeline is better, but the margin is not yet a clear win."
286:     elif delta == 0:
287:         verdict = "tie"
288:         reason = "pipeline did not beat the direct baseline."
289:     else:
290:         verdict = "baseline_better"
291:         reason = "direct baseline scored higher than the pipeline output."
292:     return DramaQualityComparison(
293:         baseline_overall_score=baseline_score,
294:         pipeline_overall_score=pipeline_score,
295:         delta=delta,
296:         verdict=verdict,
297:         reason=reason,
298:     )
299: 
300: 
301: def _blocking_issue_text(dimension: DramaQualityDimension) -> str:
302:     issue = f"{dimension.name}: {dimension.suggestion}"
303:     if dimension.evidence:
304:         issue += " 证据：" + "；".join(dimension.evidence[:3])
305:     return issue
306: 
307: 
308: def build_drama_quality_report(
309:     *,
310:     script_batch: ScriptBatch,
311:     quality_report: QualityReport | None = None,
312:     adaptation_quality_report: AdaptationQualityReport | None = None,
313:     baseline_script_batch: ScriptBatch | None = None,
314: ) -> DramaQualityReport:
315:     dimensions, warnings = _score_from_metrics(script_batch, quality_report)
316:     source_asset_dimension = _source_asset_dimension(adaptation_quality_report)
317:     dimensions.append(source_asset_dimension)
318:     overall = _overall(dimensions)
319:     if source_asset_dimension.status == "blocking":
320:         overall = min(overall, 5 if source_asset_dimension.score <= 2 else 6)
321:     blocking_issues = dedupe_quality_items([
322:         _blocking_issue_text(dimension)
323:         for dimension in dimensions
324:         if dimension.status == "blocking"
325:     ])
326:     advisory_warnings = dedupe_quality_items([
327:         f"{dimension.name}: {dimension.suggestion}"
328:         for dimension in dimensions
329:         if dimension.status == "advisory"
330:     ])
331:     if overall < 7 and not blocking_issues:
332:         advisory_warnings.append("overall drama quality below delivery target")
333:     comparison = _comparison(
334:         pipeline_score=overall,
335:         baseline_script_batch=baseline_script_batch,
336:     )
337:     if comparison and comparison.verdict in {"tie", "baseline_better"}:
338:         blocking_issues.append(
339:             "pipeline output is not better than the direct LLM baseline"
340:         )
341:     elif comparison and comparison.verdict == "pipeline_slightly_better":
342:         advisory_warnings.append(
343:             "pipeline output only slightly beats the direct LLM baseline"
344:         )
345: 
346:     rewrite_parts = dedupe_quality_items([
347:         issue.replace(": ", "：") for issue in [*blocking_issues, *advisory_warnings]
348:     ])
349:     if warnings:
350:         rewrite_parts.append("本地戏剧质检证据：" + "；".join(warnings[:5]))
351: 
352:     return DramaQualityReport(
353:         overall_score=overall,
354:         dimensions=dimensions,
355:         blocking_issues=blocking_issues,
356:         advisory_warnings=advisory_warnings,
357:         rewrite_instruction="；".join(rewrite_parts),
358:         baseline_comparison=comparison,
359:     )
360: 
361: 
362: def merge_drama_quality_into_report(
363:     quality_report: QualityReport,
364:     drama_quality_report: DramaQualityReport,
365: ) -> QualityReport:
366:     if not drama_quality_report.blocking_issues and drama_quality_report.overall_score >= 7:
367:         return quality_report
368:     if not drama_quality_report.blocking_issues:
369:         return quality_report
370:     issues = [*quality_report.blocking_issues]
371:     issues.extend(
372:         f"drama_quality: {issue}"
373:         for issue in drama_quality_report.blocking_issues
374:     )
375:     if drama_quality_report.overall_score < 7:
376:         issues.append(
377:             f"drama_quality overall below target: {drama_quality_report.overall_score}/10"
378:         )
379:     rewrite_instruction = merge_rewrite_instructions(
380:         [
381:             quality_report.rewrite_instruction,
382:             drama_quality_report.rewrite_instruction,
383:         ],
384:         blocking=True,
385:     )
386:     status = quality_report.status
387:     if status == QualityStatus.USABLE:
388:         status = QualityStatus.NEEDS_HUMAN_REVIEW
389:     return quality_report.model_copy(
390:         update={
391:             "status": status,
392:             "blocking_issues": dedupe_quality_items(issues),
393:             "rewrite_instruction": rewrite_instruction,
394:         }
395:     )
```

## File: `src/novel_drama_engine/script_quality.py`
### Lines 580-835
```
580:         explanatory_voiced_lines=len(explanatory_voiced_lines),
581:         abnormal_repetition_lines=len(abnormal_repetition_lines),
582:         title_in_action_lines=len(title_in_action_lines),
583:     )
584: 
585: 
586: def episode_quality_warnings(
587:     episode: EpisodeScript,
588:     *,
589:     strict_shooting: bool | None = None,
590: ) -> list[str]:
591:     if strict_shooting is None:
592:         strict_shooting = strict_shooting_quality_enabled()
593:     metrics = episode_quality_metrics(episode)
594:     prefix = f"EP{episode.episode:02d}"
595:     warnings: list[str] = []
596:     underfilled_episode = metrics.chars < MIN_EPISODE_CHARS or metrics.scenes < MIN_SCENES
597: 
598:     if metrics.chars < MIN_EPISODE_CHARS:
599:         warnings.append(
600:             f"{prefix} too short: {metrics.chars} chars, expected >= {MIN_EPISODE_CHARS}"
601:         )
602:     if metrics.chars > MAX_EPISODE_CHARS:
603:         warnings.append(
604:             f"{prefix} too long: {metrics.chars} chars, expected <= {MAX_EPISODE_CHARS}"
605:         )
606:     if metrics.scenes < MIN_SCENES:
607:         warnings.append(f"{prefix} has {metrics.scenes} scenes, expected >= {MIN_SCENES}")
608:     if metrics.scenes > MAX_SCENES:
609:         warnings.append(f"{prefix} has {metrics.scenes} scenes, expected <= {MAX_SCENES}")
610:     if strict_shooting and metrics.total_scene_lines < MIN_TOTAL_SCENE_LINES:
611:         warnings.append(
612:             f"{prefix} has {metrics.total_scene_lines} visible scene lines, expected >= {MIN_TOTAL_SCENE_LINES}"
613:         )
614:     if metrics.invalid_scene_headings:
615:         invalid_headings = [
616:             scene.heading
617:             for scene in episode.scenes
618:             if not has_shooting_scene_heading(scene.heading)
619:         ][:3]
620:         warnings.append(
621:             f"{prefix} has non-shooting scene headings: {', '.join(invalid_headings)}; expected like 1-1 夜-内-具体地点"
622:         )
623:     if (strict_shooting or underfilled_episode) and metrics.action_lines < MIN_ACTION_LINES:
624:         warnings.append(
625:             f"{prefix} has {metrics.action_lines} action lines, expected >= {MIN_ACTION_LINES}"
626:         )
627:     if (strict_shooting or underfilled_episode) and metrics.voiced_lines < MIN_VOICED_LINES:
628:         warnings.append(
629:             f"{prefix} has {metrics.voiced_lines} voiced lines, expected >= {MIN_VOICED_LINES}"
630:         )
631:     if strict_shooting and metrics.camera_lines < MIN_ACTION_LINES:
632:         warnings.append(
633:             f"{prefix} has weak camera direction density: {metrics.camera_lines}"
634:         )
635:     if strict_shooting and metrics.shot_language_lines < MIN_SHOT_LANGUAGE_LINES:
636:         warnings.append(
637:             f"{prefix} lacks executable shot language: {metrics.shot_language_lines}, expected >= {MIN_SHOT_LANGUAGE_LINES}"
638:         )
639:     if (strict_shooting or underfilled_episode) and metrics.linked_shot_lines < 3:
640:         warnings.append(
641:             f"{prefix} lacks shot-to-shot linkage: {metrics.linked_shot_lines}, expected >= 3"
642:         )
643:     if strict_shooting and metrics.invalid_action_format_lines:
644:         warnings.append(
645:             f"{prefix} has {metrics.invalid_action_format_lines} action lines violating △景别+运镜 opening format"
646:         )
647:     if metrics.strong_lines < MIN_STRONG_LINES:
648:         warnings.append(
649:             f"{prefix} lacks high-pressure dialogue: {metrics.strong_lines} strong lines"
650:         )
651:     if metrics.long_voiced_lines:
652:         warnings.append(
653:             f"{prefix} has {metrics.long_voiced_lines} verbose voiced lines, expected <= {MAX_VOICED_LINE_CHARS} chars each"
654:         )
655:     if metrics.opening_conflict_lines < 1:
656:         warnings.append(f"{prefix} opening does not explode in the first 8 beats")
657:     if metrics.exposed_analysis_lines:
658:         warnings.append(
659:             f"{prefix} exposes hook/watch_reason analysis in user-visible script lines"
660:         )
661:     if metrics.abstract_action_lines:
662:         warnings.append(
663:             f"{prefix} has abstract action lines instead of executable shots: {metrics.abstract_action_lines}"
664:         )
665:     if metrics.explanatory_voiced_lines:
666:         warnings.append(
667:             f"{prefix} has explanatory/value-summary voiced lines: {metrics.explanatory_voiced_lines}"
668:         )
669:     if metrics.abnormal_repetition_lines:
670:         warnings.append(
671:             f"{prefix} has abnormal repeated words/phrases in visible lines: {metrics.abnormal_repetition_lines}"
672:         )
673:     if metrics.title_in_action_lines:
674:         warnings.append(
675:             f"{prefix} repeats episode title in action lines: {metrics.title_in_action_lines}"
676:         )
677:     if has_template_mismatch(_episode_visible_text(episode)):
678:         warnings.append(f"{prefix} has genre template mismatch in user-visible script lines")
679:     if not has_performed_ending_hook(episode):
680:         warnings.append(
681:             f"{prefix} cliffhanger is not performed in the final scene last 2 lines"
682:         )
683: 
684:     for scene in episode.scenes:
685:         for index, line in enumerate(scene.lines[:-1]):
686:             if line.kind == "os" and scene.lines[index + 1].kind != "action":
687:                 warnings.append(f"{prefix} OS at {scene.heading} is not followed by action")
688: 
689:     if not episode.cliffhanger.strip() or not has_cliffhanger_force(episode.cliffhanger):
690:         warnings.append(f"{prefix} cliffhanger is too soft")
691:     if has_explanatory_cliffhanger(episode.cliffhanger):
692:         warnings.append(
693:             f"{prefix} cliffhanger field is explanatory; use the performed final hook line/action"
694:         )
695:     if not cliffhanger_field_is_performed(episode):
696:         warnings.append(
697:             f"{prefix} cliffhanger field is not present in the final scene tail"
698:         )
699: 
700:     return warnings
701: 
702: 
703: def episode_repair_mode(
704:     episode: EpisodeScript,
705:     base_instruction: str = "",
706:     *,
707:     allow_full_rewrite: bool = True,
708: ) -> EpisodeRepairMode:
709:     metrics = episode_quality_metrics(episode)
710:     warnings = episode_quality_warnings(episode, strict_shooting=True)
711:     warning_text = "\n".join([*warnings, base_instruction]).lower()
712:     structural_collapse = (
713:         metrics.chars < 500
714:         or metrics.scenes < 2
715:         or metrics.total_scene_lines < 12
716:         or metrics.action_lines < 4
717:         or metrics.voiced_lines < 6
718:     )
719:     if structural_collapse and allow_full_rewrite:
720:         return "full_episode_rewrite"
721: 
722:     if any(token in warning_text for token in CREATIVE_REPAIR_TOKENS):
723:         return "creative_episode_repair"
724: 
725:     if warnings and all(
726:         any(token in warning for token in FORMAT_ONLY_WARNING_TOKENS)
727:         for warning in warnings
728:     ):
729:         return "format_patch"
730: 
731:     if warnings and all(
732:         any(token in warning for token in ENDING_ONLY_WARNING_TOKENS)
733:         for warning in warnings
734:     ):
735:         return "ending_hook_patch"
736: 
737:     if any(token in base_instruction for token in ("结尾", "钩子", "断点", "cliffhanger")):
738:         return "ending_hook_patch"
739:     if any(token in base_instruction for token in ("格式", "action", "镜头格式", "场景标题")):
740:         return "format_patch"
741:     return "creative_episode_repair"
742: 
743: 
744: def build_current_episode_repair_packet(
745:     episode: EpisodeScript,
746:     base_instruction: str = "",
747:     *,
748:     allow_full_rewrite: bool = True,
749:     source_evidence_targets: list[str] | None = None,
750: ) -> CurrentEpisodeRepairPacket:
751:     source_evidence_targets = list(dict.fromkeys(source_evidence_targets or []))
752:     source_contract_repair = bool(source_evidence_targets) or any(
753:         token in base_instruction
754:         for token in (
755:             "source_evidence",
756:             "原文证据",
757:             "源文证据",
758:             "原文偏离",
759:             "源文偏离",
760:             "源文相似",
761:             "source similarity",
762:             "source_asset_preservation",
763:             "方法论阻断",
764:             "强原文轻改失败",
765:             "C0/C1",
766:         )
767:     )
768:     mode = episode_repair_mode(
769:         episode,
770:         base_instruction,
771:         allow_full_rewrite=allow_full_rewrite,
772:     )
773:     if source_contract_repair and mode in {"format_patch", "ending_hook_patch"}:
774:         mode = "creative_episode_repair"
775:     warnings = episode_quality_warnings(episode, strict_shooting=True)
776:     mode_scope = {
777:         "format_patch": (
778:             "只修不合格 action 行、场景标题或外露分析字段；其余场景、对白、人物关系、"
779:             "事件因果、原文资产和结尾钩子照抄当前集旧稿。"
780:         ),
781:         "ending_hook_patch": (
782:             "只修最后一场最后 8-12 行和必要短对白；前文场景、人物动机、证据来源、"
783:             "主动方和已演出的原文资产照抄当前集旧稿。"
784:         ),
785:         "creative_episode_repair": (
786:             "只修被质检点名的 OOC、原文偏离、情绪递进、冲突因果或跨集承接问题；"
787:             "已合格场次和 C1 名场面尽量照抄当前集旧稿。"
788:         ),
789:         "full_episode_rewrite": (
790:             "当前集结构崩坏或严重缺量，允许整集重写；仍必须以当前集已出现的人物、"
791:             "事件意图、原文锚点和上下集边界为基准。"
792:         ),
793:     }
794:     if source_contract_repair:
795:         mode_scope[mode] = (
796:             "回到当前集 source packet、source_annotation 和 episode_cut_table 重建本集内容；"
797:             "只保留旧稿中能被当前集原文契约证明的对白、动作、人物状态和上下集承接。"
798:         )
799:     scene_headings = [scene.heading for scene in episode.scenes]
800:     characters = sorted({character for scene in episode.scenes for character in scene.characters})
801:     protected_elements = [
802:         f"title: {episode.title}",
803:         "scene_headings: " + " / ".join(scene_headings),
804:         "characters: " + "、".join(characters),
805:         f"hook_3s: {episode.hook_3s}",
806:         f"cliffhanger: {episode.cliffhanger}",
807:     ]
808:     if episode.state_update:
809:         protected_elements.append(
810:             "state_update_keys: " + "、".join(str(key) for key in episode.state_update)
811:         )
812:     if source_contract_repair:
813:         protected_elements = [
814:             f"episode: {episode.episode}",
815:             "existing_episode_to_rewrite 仅用于定位失败，不作为剧情边界或资产边界。",
816:         ]
817:     editable_targets = [
818:         *source_evidence_targets,
819:         *(warnings or [base_instruction.strip() or "未点名具体本地缺口"]),
820:     ]
821:     return CurrentEpisodeRepairPacket(
822:         episode=episode.episode,
823:         repair_mode=mode,
824:         baseline_policy=(
825:             "当前集原文契约是唯一内容基准。旧稿只作为问题定位参考；"
826:             "必须用当前集 source packet、source_annotation 和 episode_cut_table 覆盖旧稿中无原文依据的场景、动作、台词、道具和因果。"
827:             if source_contract_repair
828:             else (
829:                 "当前集旧稿是唯一文本基准。修复只能在 baseline_episode_text 的基础上做最小必要改动；"
830:                 "不得用 episode_plan、source packet 或全局质检意见覆盖当前集已成立的正片内容。"
831:             )
832:         ),
833:         baseline_episode_text=render_episode(episode),
834:         allowed_change_scope=mode_scope[mode],
835:         editable_targets=editable_targets,
```
### Lines 845-1040
```
845:             "不得跨集挪用其他 episode_source_packet 的事件、道具或真相揭示。",
846:         ],
847:         forbidden_changes=[
848:             "不得新增无原文依据的新剧情、新道具、新证据或新狠话",
849:             "不得把预谋改成冲动、把被动承受改成主动索取、把克制人物改成歇斯底里",
850:             "不得为了补格式或镜头密度增加水对白、空镜、泛场景或新支线",
851:         ],
852:     )
853: 
854: 
855: def episode_repair_instruction(
856:     episode: EpisodeScript,
857:     base_instruction: str = "",
858:     *,
859:     allow_full_rewrite: bool = True,
860: ) -> str:
861:     metrics = episode_quality_metrics(episode)
862:     warnings = episode_quality_warnings(episode, strict_shooting=True)
863:     mode = episode_repair_mode(
864:         episode,
865:         base_instruction,
866:         allow_full_rewrite=allow_full_rewrite,
867:     )
868:     missing_chars = max(0, MIN_EPISODE_CHARS - metrics.chars)
869:     missing_actions = max(0, MIN_ACTION_LINES - metrics.action_lines)
870:     missing_voiced = max(0, MIN_VOICED_LINES - metrics.voiced_lines)
871:     missing_shots = max(0, MIN_SHOT_LANGUAGE_LINES - metrics.shot_language_lines)
872:     missing_links = max(0, 3 - metrics.linked_shot_lines)
873: 
874:     quality_snapshot = (
875:         "当前本地质检："
876:         f"{metrics.chars} 字、{metrics.scenes} 场、"
877:         f"{metrics.action_lines} 条 action、{metrics.voiced_lines} 条对白/OS/VO、"
878:         f"{metrics.shot_language_lines} 条可执行镜头、"
879:         f"{metrics.linked_shot_lines} 条镜头衔接。"
880:     )
881:     full_rewrite_parts = [
882:         "修复级别：结构崩坏整集重写。",
883:         f"第 {episode.episode} 集结构崩坏或严重缺量，允许整集重写；不要摘要复述 existing_episode。",
884:         quality_snapshot,
885:         (
886:             "本次重写硬目标：900-1500 字、优先 3 场、至少 10 条 action、"
887:             "至少 18 条 dialogue/os/vo、至少 28 条用户可见 scene line、"
888:             "至少 8 条 action 同时含景别+运镜、"
889:             "至少 3 条 action 含切到/切回/反打/声音先入/音效/BGM/道具特写/前景。"
890:         ),
891:         (
892:             "action 行硬格式：每条 action.text 必须以“△景别+运镜”开头，例如"
893:             "“△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节”。"
894:             "禁止以“△女主/△温铮/△他/△她/△门外/△突然”直接开头。"
895:         ),
896:         (
897:             "必须补足缺口："
898:             f"至少增加 {missing_chars} 字、{missing_actions} 条 action、"
899:             f"{missing_voiced} 条对白/OS/VO、{missing_shots} 条可执行镜头、"
900:             f"{missing_links} 条镜头衔接。"
901:         ),
902:         (
903:             "结构要求：第一场前 8 个 beat 直接爆冲突；中段必须有一次假打脸或期待落空；"
904:             "最后一场倒数第 2 行必须是 action，且包含景别、运镜、道具/动作和衔接词；"
905:             "最后一行必须是强对白/强 OS/强 VO 或动作未完成的道具特写。"
906:         ),
907:         (
908:             "镜头写法禁止抽象：不要写“眼神复杂、气氛凝固、若有所思、转身离开”作为钩子；"
909:             "要写清镜头怎么拍、道具在哪里、角色手/脸/视线如何变化、声音如何切入下一拍。"
910:         ),
911:     ]
912: 
913:     focused_parts_by_mode: dict[EpisodeRepairMode, list[str]] = {
914:         "format_patch": [
915:             "修复级别：格式局部修复。",
916:             f"第 {episode.episode} 集只修不合格 action 行、场景标题或外露分析字段；不要整集重写。",
917:             quality_snapshot,
918:             (
919:                 "允许改动范围：只改被本地质检点名的行，以及为保持语义连贯必须同步的极少量相邻行。"
920:                 "标题、场景顺序、人物关系、事件因果、原文资产、结尾钩子和已合格对白必须保留。"
921:             ),
922:             (
923:                 "格式目标：action 行以“△景别+运镜”开头，补齐构图/道具/表情/声音/切镜衔接；"
924:                 "不要新增无原文依据的新道具、新证据、新狠话。"
925:             ),
926:         ],
927:         "ending_hook_patch": [
928:             "修复级别：结尾钩子局部修复。",
929:             f"第 {episode.episode} 集只修最后一场最后 8-12 行和必要短对白；不要整集重写。",
930:             quality_snapshot,
931:             f"当前尾部：{final_scene_tail_text(episode, line_count=8)!r}",
932:             (
933:                 "允许改动范围：保留前文场景、人物动机、证据来源、主动方和已演出的原文资产；"
934:                 "只把结尾停在身份将揭未揭、证据将爆未爆、威胁将落未落或强问题未回答的位置。"
935:             ),
936:             (
937:                 "cliffhanger 字段必须直接填写最后 4 行里已经演出来的钩子台词或动作；"
938:                 "禁止写说明句，禁止用转身离开、明天再说、黑屏、普通背影收束。"
939:             ),
940:         ],
941:         "creative_episode_repair": [
942:             "修复级别：单集创作修复。",
943:             f"第 {episode.episode} 集回到 source packet、Story Bible 和 existing_episode 做定向修复；不要整集洗稿。",
944:             quality_snapshot,
945:             (
946:                 "允许改动范围：只修被点名的 OOC、原文偏离、情绪递进、冲突因果或跨集承接问题。"
947:                 "已合格场次、已保留的 C1 名场面、人物关系和结尾边界必须尽量照抄。"
948:             ),
949:             (
950:                 "如果原文本身已有强冲突和爆款属性，只做视听化增强和短台词压缩；"
951:                 "不得为了更爽新增改变主动方、动机、关键决定时机或证据来源的剧情。"
952:             ),
953:         ],
954:         "full_episode_rewrite": full_rewrite_parts,
955:     }
956:     parts = focused_parts_by_mode[mode]
957:     if warnings:
958:         parts.append("本集本地阻断项：\n- " + "\n- ".join(warnings))
959:     if base_instruction.strip():
960:         parts.append("全局修复背景（仅供参考，必须优先执行本集修复级别）：\n" + base_instruction.strip())
961:     return "\n".join(part for part in parts if part)
962: 
963: 
964: def episode_needs_hook_dialogue_polish(episode: EpisodeScript) -> bool:
965:     warnings = episode_quality_warnings(episode)
966:     return any(
967:         any(token in warning for token in HOOK_DIALOGUE_POLISH_WARNING_TOKENS)
968:         for warning in warnings
969:     )
970: 
971: 
972: def hook_dialogue_polish_instruction(
973:     episode: EpisodeScript,
974:     base_instruction: str = "",
975: ) -> str:
976:     metrics = episode_quality_metrics(episode)
977:     warnings = episode_quality_warnings(episode, strict_shooting=True)
978:     missing_chars = max(0, MIN_EPISODE_CHARS - metrics.chars)
979:     missing_voiced = max(0, MIN_VOICED_LINES - metrics.voiced_lines)
980:     missing_links = max(0, 3 - metrics.linked_shot_lines)
981: 
982:     parts = [
983:         (
984:             f"第 {episode.episode} 集进入结尾钩子/对白密度二次编译。"
985:             "这是 focused pass，不要整集重写，不要改掉已经合格的场次、人物关系和镜头动作。"
986:         ),
987:         (
988:             "只允许做三类改动："
989:             "1. 在最后一场或倒数第二场补短对白/OS/VO，使对白密度达标；"
990:             "2. 修复 OS 后缺少动作承接的问题；"
991:             "3. 重写最后一场最后 8-12 行，让结尾停在未回答的问题、身份将揭、证据将爆、威胁将落下或动作未完成。"
992:         ),
993:         (
994:             "当前本地质检："
995:             f"{metrics.chars} 字、{metrics.voiced_lines} 条对白/OS/VO、"
996:             f"{metrics.linked_shot_lines} 条镜头衔接、cliffhanger={episode.cliffhanger!r}。"
997:             f"最后尾部={final_scene_tail_text(episode)!r}。"
998:         ),
999:         (
1000:             "本次 focused 目标："
1001:             f"至少补 {missing_chars} 字、{missing_voiced} 条短对白/OS/VO、"
1002:             f"{missing_links} 条镜头衔接；最后两行必须形成追更断点。"
1003:         ),
1004:         (
1005:             "结尾禁止：转身离开、我需要时间、明天再说、画面冻结、普通背影、情绪总结、"
1006:             "把秘密说完、把冲突解决完、让角色退场收束。"
1007:         ),
1008:         (
1009:             "结尾必须：倒数第 2 行是 action，且以“△景别+运镜”开头，包含道具/动作和切到/切回/反打/"
1010:             "声音先入/音效/BGM/道具特写/前景之一；最后 1 行是强对白/强 OS/强 VO，"
1011:             "或一个动作未完成的道具特写。"
1012:         ),
1013:         (
1014:             "cliffhanger 字段硬规则：必须直接填写最后 4 行里已经演出来的钩子台词或动作，"
1015:             "例如“这东西，为什么在你手里？”；禁止写“留下悬念/关于真实身份的悬念/气氛紧张”等说明句。"
1016:         ),
1017:         (
1018:             "推荐最后一句模板："
1019:             "“你敢再说一遍？”、“她不是你能碰的人。”、“这东西，为什么在你手里？”、"
1020:             "“你到底是谁？”、“别信她，她会害死你。”"
1021:         ),
1022:         (
1023:             "输出仍必须是完整 EpisodeScript JSON，但除最后 8-12 行和必要短对白补足外，其余内容照抄 existing_episode。"
1024:         ),
1025:     ]
1026:     if warnings:
1027:         parts.append("本集剩余阻断项：\n- " + "\n- ".join(warnings))
1028:     if base_instruction.strip():
1029:         parts.append("全局修复背景（仅供参考，不得覆盖 focused 目标）：\n" + base_instruction.strip())
1030:     return "\n".join(part for part in parts if part)
1031: 
1032: 
1033: def _parse_target_episode_range(target_episode_range: str) -> tuple[int, int] | None:
1034:     match = re.fullmatch(r"EP(\d{2,})-EP(\d{2,})", target_episode_range.strip())
1035:     if not match:
1036:         return None
1037:     start_episode = int(match.group(1))
1038:     end_episode = int(match.group(2))
1039:     if end_episode < start_episode:
1040:         return None
```
### Lines 1220-1325
```
1220:                 ),
1221:                 _similarity_issue(
1222:                     left=left,
1223:                     right=right,
1224:                     kind="action_chain",
1225:                     score=action_score,
1226:                     threshold=NOVELTY_ACTION_BLOCKING_SCORE,
1227:                     evidence=[
1228:                         _episode_action_text(left).split("\n")[0][:120],
1229:                         _episode_action_text(right).split("\n")[0][:120],
1230:                     ],
1231:                     suggestion="重写动作链和关键视觉道具，不要复用同一套镜头模板。",
1232:                 ),
1233:                 _similarity_issue(
1234:                     left=left,
1235:                     right=right,
1236:                     kind="dialogue_pattern",
1237:                     score=dialogue_score,
1238:                     threshold=NOVELTY_DIALOGUE_BLOCKING_SCORE,
1239:                     evidence=[
1240:                         _episode_dialogue_pattern(left)[:140],
1241:                         _episode_dialogue_pattern(right)[:140],
1242:                     ],
1243:                     suggestion="改变施压/反击对白结构，让角色本集诉求和信息增量发生变化。",
1244:                 ),
1245:                 _similarity_issue(
1246:                     left=left,
1247:                     right=right,
1248:                     kind="cliffhanger",
1249:                     score=cliffhanger_score,
1250:                     threshold=NOVELTY_CLIFFHANGER_BLOCKING_SCORE,
1251:                     evidence=[left.cliffhanger, right.cliffhanger],
1252:                     suggestion="结尾钩子要换成新的未回答问题，避免同类证据/同类威胁连续重复。",
1253:                 ),
1254:             ]
1255:             issues.extend(issue for issue in maybe_issues if issue is not None)
1256: 
1257:     blocking_issues = dedupe_quality_items(
1258:         [_issue_text(issue) for issue in issues if issue.severity == "blocking"]
1259:     )
1260:     advisory_warnings = dedupe_quality_items(
1261:         [_issue_text(issue) for issue in issues if issue.severity == "advisory"]
1262:     )
1263:     if blocking_issues:
1264:         score = max(0, 10 - len(blocking_issues) * 2 - len(advisory_warnings))
1265:     elif advisory_warnings:
1266:         score = max(6, 10 - len(advisory_warnings))
1267:     else:
1268:         score = 10
1269: 
1270:     rewrite_instruction = ""
1271:     if blocking_issues or advisory_warnings:
1272:         repair_targets = sorted(
1273:             {
1274:                 episode
1275:                 for issue in issues
1276:                 for episode in issue.episodes
1277:                 if issue.severity == "blocking"
1278:             }
1279:         )
1280:         target_text = (
1281:             "、".join(f"EP{episode:02d}" for episode in repair_targets)
1282:             if repair_targets
1283:             else "相似度最高的集"
1284:         )
1285:         issue_lines = blocking_issues[:8] or advisory_warnings[:8]
1286:         rewrite_instruction = (
1287:             "跨集新鲜度不足，必须按集重写而不是局部替换台词。优先处理 "
1288:             f"{target_text}。\n"
1289:             "修复规则：每集必须有不同的冲突场域、施压动作、信息增量、视觉道具和结尾未回答问题；"
1290:             "禁止复用同一套场景三段式、同一组人物进出场和同一句式反击。\n"
1291:             "检测到的问题：\n- "
1292:             + "\n- ".join(issue_lines)
1293:         )
1294: 
1295:     return ScriptNoveltyReport(
1296:         overall_score=score,
1297:         episode_profiles=profiles,
1298:         similarity_issues=issues,
1299:         blocking_issues=blocking_issues,
1300:         advisory_warnings=advisory_warnings,
1301:         rewrite_instruction=rewrite_instruction,
1302:     )
1303: 
1304: 
1305: def merge_script_novelty_into_quality_report(
1306:     quality_report: QualityReport,
1307:     novelty_report: ScriptNoveltyReport,
1308: ) -> QualityReport:
1309:     if not novelty_report.blocking_issues:
1310:         return quality_report
1311:     blocking_issues = dedupe_quality_items(
1312:         [
1313:             *quality_report.blocking_issues,
1314:             *[
1315:                 f"script_novelty: {issue}"
1316:                 for issue in novelty_report.blocking_issues
1317:             ],
1318:         ]
1319:     )
1320:     return quality_report.model_copy(
1321:         update={
1322:             "status": QualityStatus.NEEDS_REWRITE
1323:             if quality_report.status == QualityStatus.USABLE
1324:             else quality_report.status,
1325:             "blocking_issues": blocking_issues,
```
### Lines 1369-1415
```
1369:                         issue.kind,
1370:                         f"{issue.score:.2f}",
1371:                         issue.severity,
1372:                         issue.suggestion.replace("|", "/"),
1373:                     ]
1374:                 )
1375:                 + " |"
1376:             )
1377:     if report.rewrite_instruction:
1378:         lines.extend(["", "## Rewrite Instruction", "", report.rewrite_instruction])
1379:     lines.append("")
1380:     return "\n".join(lines)
1381: 
1382: 
1383: def script_batch_quality_warnings(
1384:     script_batch: ScriptBatch,
1385:     target_episode_range: str,
1386: ) -> list[str]:
1387:     parsed_range = _parse_target_episode_range(target_episode_range)
1388:     if parsed_range is None:
1389:         return [
1390:             f"target_episode_range is malformed: {target_episode_range}; expected EP01-EP05"
1391:         ]
1392: 
1393:     start_episode, end_episode = parsed_range
1394:     expected_episodes = list(range(start_episode, end_episode + 1))
1395:     actual_episodes = [episode.episode for episode in script_batch.episodes]
1396:     warnings: list[str] = []
1397: 
1398:     if actual_episodes != expected_episodes:
1399:         expected_label = ",".join(f"EP{episode:02d}" for episode in expected_episodes)
1400:         actual_label = ",".join(f"EP{episode:02d}" for episode in actual_episodes)
1401:         warnings.append(
1402:             f"script episodes mismatch target range {target_episode_range}: expected {expected_label}, got {actual_label}"
1403:         )
1404: 
1405:     if len(actual_episodes) != len(set(actual_episodes)):
1406:         warnings.append("script episodes contain duplicate episode numbers")
1407: 
1408:     return warnings
```

## File: `src/novel_drama_engine/quality_text.py`
### Lines 1-140
```
1: from __future__ import annotations
2: 
3: import re
4: from collections.abc import Iterable
5: 
6: 
7: POSITIVE_QUALITY_HINTS = (
8:     "no blocking issues detected",
9:     "accurately map",
10:     "accurately maps",
11:     "key highlights maintained",
12:     "ensure that when filming",
13:     "all checks passed",
14:     "no blocking",
15: )
16: 
17: EPISODE_RANGE_PATTERNS = (
18:     re.compile(
19:         r"\bEP\s*0*(\d{1,3})\s*(?:-|~|–|—|至|到)\s*(?:EP\s*)?0*(\d{1,3})\b",
20:         re.IGNORECASE,
21:     ),
22:     re.compile(r"第\s*0*(\d{1,3})\s*(?:-|~|–|—|至|到)\s*0*(\d{1,3})\s*集"),
23: )
24: 
25: EPISODE_REF_PATTERNS = (
26:     re.compile(r"\bEP\s*0*(\d{1,3})\b", re.IGNORECASE),
27:     re.compile(r"第\s*0*(\d{1,3})\s*集"),
28: )
29: 
30: 
31: def _compact_key(text: str) -> str:
32:     return re.sub(r"\s+", "", text).replace("：", ":").lower()
33: 
34: 
35: def _is_positive_advice(text: str) -> bool:
36:     lowered = text.lower()
37:     return any(hint in lowered for hint in POSITIVE_QUALITY_HINTS)
38: 
39: 
40: def _clean_segment(text: str) -> str:
41:     text = re.sub(r"\s+", " ", text.strip())
42:     text = re.sub(r"^[-*•]\s*", "", text)
43:     return text.strip("；; ")
44: 
45: 
46: def _segments(text: str) -> list[str]:
47:     parts: list[str] = []
48:     for line in re.split(r"[\r\n]+", text):
49:         line = _clean_segment(line)
50:         if not line:
51:             continue
52:         parts.extend(_clean_segment(part) for part in re.split(r"[；;]+", line))
53:     return [part for part in parts if part]
54: 
55: 
56: def dedupe_quality_items(
57:     items: Iterable[str],
58:     *,
59:     drop_positive: bool = True,
60: ) -> list[str]:
61:     cleaned: list[str] = []
62:     seen: set[str] = set()
63:     for item in items:
64:         item = _clean_segment(str(item))
65:         if not item:
66:             continue
67:         if drop_positive and _is_positive_advice(item):
68:             continue
69:         key = _compact_key(item)
70:         if key in seen:
71:             continue
72:         seen.add(key)
73:         cleaned.append(item)
74:     return cleaned
75: 
76: 
77: def merge_rewrite_instructions(
78:     parts: Iterable[str],
79:     *,
80:     blocking: bool,
81:     max_segments: int = 28,
82: ) -> str:
83:     merged: list[str] = []
84:     seen: set[str] = set()
85:     for part in parts:
86:         if not str(part).strip():
87:             continue
88:         for segment in _segments(str(part)):
89:             if blocking and _is_positive_advice(segment):
90:                 continue
91:             key = _compact_key(segment)
92:             if key in seen:
93:                 continue
94:             seen.add(key)
95:             merged.append(segment)
96:             if len(merged) >= max_segments:
97:                 return "；".join(merged)
98:     return "；".join(merged)
99: 
100: 
101: def _episode_refs(text: str) -> set[int]:
102:     refs: set[int] = set()
103:     for pattern in EPISODE_RANGE_PATTERNS:
104:         for start_text, end_text in pattern.findall(text):
105:             start, end = int(start_text), int(end_text)
106:             if end < start:
107:                 start, end = end, start
108:             refs.update(range(start, end + 1))
109:     for pattern in EPISODE_REF_PATTERNS:
110:         refs.update(int(match) for match in pattern.findall(text))
111:     return refs
112: 
113: 
114: def filter_quality_text_for_episode(text: str, episode_number: int) -> str:
115:     scoped: list[str] = []
116:     for segment in _segments(text):
117:         refs = _episode_refs(segment)
118:         if refs and episode_number not in refs:
119:             continue
120:         scoped.append(segment)
121:     return merge_rewrite_instructions(scoped, blocking=True)
```

## File: `src/novel_drama_engine/lean_flow.py`
### Lines 1-260
```
1: from __future__ import annotations
2: 
3: import re
4: 
5: from novel_drama_engine.models import (
6:     EpisodeContext,
7:     EpisodeCut,
8:     EpisodeCutTable,
9:     EpisodeSourcePacket,
10:     EpisodeSourcePackets,
11:     ProductionSpec,
12:     SourceAnalysis,
13:     SourceAnnotation,
14:     SourceAnnotationEpisode,
15:     StoryBible,
16: )
17: 
18: 
19: PSYCHOLOGICAL_MARKERS = (
20:     "僵",
21:     "震惊",
22:     "心碎",
23:     "屈辱",
24:     "害怕",
25:     "克制",
26:     "冷静",
27:     "决绝",
28:     "清醒",
29:     "委屈",
30:     "愣",
31:     "眼眶",
32:     "泪",
33: )
34: 
35: 
36: def _dedupe(items: list[str]) -> list[str]:
37:     return [item for item in dict.fromkeys(item.strip() for item in items if item.strip())]
38: 
39: 
40: def _sentence_snippets(text: str, markers: tuple[str, ...], *, limit: int = 4) -> list[str]:
41:     snippets: list[str] = []
42:     for part in re.split(r"(?<=[。！？!?])|\n+", text):
43:         cleaned = part.strip()
44:         if cleaned and any(marker in cleaned for marker in markers):
45:             snippets.append(cleaned[:120])
46:         if len(snippets) >= limit:
47:             break
48:     return _dedupe(snippets)
49: 
50: 
51: def _packet_core_conflict(packet: EpisodeSourcePacket, fallback: str) -> str:
52:     if packet.source_anchor.strip():
53:         return packet.source_anchor.strip()
54:     if packet.c1_must_keep_assets:
55:         return packet.c1_must_keep_assets[0]
56:     return fallback
57: 
58: 
59: def build_production_spec() -> ProductionSpec:
60:     return ProductionSpec(
61:         primary_output="creative_script",
62:         script_priorities=[
63:             "创作稿先成立：人物动机、冲突因果、情绪递进和对白真实优先。",
64:             "原文标注稿与本集 source packet 是首稿最高优先级基准。",
65:             "执行稿信息后移：景别、运镜、BGM 只补足可拍性，不得污染剧情文本。",
66:         ],
67:         format_rules=[
68:             "第X集 + X-X 日/夜-内/外-具体地点 + 人物 + 正片行。",
69:             "禁止外露 3秒Hook、主情绪、消费理由、观众要看、本集看点。",
70:         ],
71:         vo_os_rules=[
72:             "OS/VO 必须服务动作或选择，下一行要承接可见动作、沉默决定或关系变化。",
73:             "屏幕字幕类解释优先转为角色 VO/OS 或短对白，不单独写说明性字幕。",
74:         ],
75:         dialogue_rules=[
76:             "台词短、口语、带潜台词，单句只表达一个动作或情绪。",
77:             "不得把克制人物写成歇斯底里，不得用解释型长句替代戏。",
78:         ],
79:         shooting_rules=[
80:             "动作行必须可拍，含主体、动作、对象和当场后果。",
81:             "镜头信息只服务情绪和信息，不为了凑格式增加空镜和水动作。",
82:         ],
83:         delivery_rules=[
84:             "首稿产物是 creative_script；通过质检后再派生 shooting_script/export。",
85:             "源文相似度低于 5/10 时，必须回到 source_annotation 定向修复。",
86:         ],
87:     )
88: 
89: 
90: def build_source_annotation(
91:     *,
92:     source_text: str,
93:     source_analysis: SourceAnalysis,
94:     episode_context: EpisodeContext,
95:     story_bible: StoryBible,
96:     episode_source_packets: EpisodeSourcePackets,
97: ) -> SourceAnnotation:
98:     episodes: list[SourceAnnotationEpisode] = []
99:     for packet in episode_source_packets.packets:
100:         must_keep_events = _dedupe([*packet.c0_facts, packet.source_anchor])
101:         must_keep_assets = _dedupe([*packet.c1_must_keep_assets, *(packet.source_evidence_assets or [])])
102:         psychological_beats = _sentence_snippets(packet.source_excerpt, PSYCHOLOGICAL_MARKERS)
103:         removable_passages = _dedupe([*packet.c3_compress_assets, *source_analysis.low_value_passages[:3]])
104:         episodes.append(
105:             SourceAnnotationEpisode(
106:                 episode=packet.episode,
107:                 source_anchor=packet.source_anchor,
108:                 source_excerpt=packet.source_excerpt,
109:                 core_conflict=_packet_core_conflict(packet, story_bible.mainline),
110:                 must_keep_events=must_keep_events,
111:                 must_keep_assets=must_keep_assets,
112:                 must_keep_lines=packet.golden_lines,
113:                 psychological_beats=psychological_beats,
114:                 visual_assets=_dedupe(packet.c2_visual_assets),
115:                 removable_passages=removable_passages,
116:                 forbidden_changes=_dedupe(
117:                     [*packet.c4_forbidden_additions, *story_bible.forbidden_changes]
118:                 ),
119:                 active_party=packet.active_party,
120:                 key_decision_timing=packet.key_decision_timing,
121:             )
122:         )
123: 
124:     return SourceAnnotation(
125:         north_star="原文标注稿是首稿最高优先级基准",
126:         global_must_keep=_dedupe(story_bible.immutable_facts),
127:         global_forbidden_changes=story_bible.forbidden_changes,
128:         removable_passages=source_analysis.low_value_passages,
129:         episodes=episodes,
130:     )
131: 
132: 
133: def build_episode_cut_table(
134:     *,
135:     episode_context: EpisodeContext,
136:     episode_source_packets: EpisodeSourcePackets,
137: ) -> EpisodeCutTable:
138:     cuts: list[EpisodeCut] = []
139:     for packet in episode_source_packets.packets:
140:         core_conflict = _packet_core_conflict(packet, packet.source_excerpt[:40])
141:         cuts.append(
142:             EpisodeCut(
143:                 episode=packet.episode,
144:                 source_anchor=packet.source_anchor,
145:                 core_conflict=core_conflict,
146:                 title_seed=core_conflict[:18],
147:                 ending_hook_seed=packet.handoff_requirement
148:                 or (packet.c1_must_keep_assets[-1] if packet.c1_must_keep_assets else core_conflict),
149:             )
150:         )
151:     return EpisodeCutTable(
152:         target_episode_range=episode_context.target_episode_range,
153:         cuts=cuts,
154:     )
```

## File: `src/novel_drama_engine/llm.py`
### Lines 250-445
```
250:                 else output_tokens
251:             ),
252:             total_tokens=total_tokens,
253:         )
254: 
255:     def complete(self, *, system: str, user: str, response_model: type[T]) -> T:
256:         self.last_usage = None
257:         self.last_raw_response = None
258:         if self._use_chat_json:
259:             return self._complete_with_chat_json(
260:                 system=system,
261:                 user=user,
262:                 response_model=response_model,
263:             )
264: 
265:         try:
266:             with _hard_timeout(self._call_timeout_seconds):
267:                 response = self._client.responses.parse(
268:                     model=self._model,
269:                     input=[
270:                         {"role": "system", "content": system},
271:                         {"role": "user", "content": user},
272:                     ],
273:                     text_format=response_model,
274:                 )
275:         except Exception as exc:
276:             raise _wrap_provider_exception(
277:                 prefix="OpenAI request failed",
278:                 response_model=response_model,
279:                 exc=exc,
280:             ) from exc
281:         self._record_usage(getattr(response, "usage", None))
282:         response_payload: Any = (
283:             response.model_dump(mode="json")
284:             if hasattr(response, "model_dump")
285:             else str(response)
286:         )
287:         self.last_raw_response = {
288:             "provider": "responses",
289:             "model": self._model,
290:             "response_model": response_model.__name__,
291:             "response": response_payload,
292:         }
293:         parsed = getattr(response, "output_parsed", None)
294:         if parsed is None:
295:             raise LLMResponseError(
296:                 f"OpenAI returned no parsed output for {response_model.__name__}"
297:             )
298:         if not isinstance(parsed, response_model):
299:             return response_model.model_validate(parsed)
300:         return parsed
301: 
302:     def _complete_with_chat_json(
303:         self,
304:         *,
305:         system: str,
306:         user: str,
307:         response_model: type[T],
308:     ) -> T:
309:         schema = response_model.model_json_schema()
310:         top_level_keys = ", ".join(schema.get("properties", {}).keys())
311:         format_instruction = (
312:             f"Generate one JSON object instance for {response_model.__name__}. "
313:             "Return raw data JSON only. The response must start with { and end with }. "
314:             "Do not output the schema itself. Do not wrap the JSON in markdown. "
315:             "Do not emit multiple JSON objects, explanations, comments, or trailing prose. "
316:             f"The top-level keys must be: {top_level_keys}. "
317:             "If the task asks for a wrapper object, do not output a nested item directly. "
318:             "Do not include schema-only keys such as properties, required, $defs, type, or title "
319:             "unless they are explicitly part of the requested data. "
320:             "Use this JSON Schema only as a validation reference:\n"
321:             f"{json.dumps(schema, ensure_ascii=False)}"
322:         )
323:         base_messages = [
324:             {"role": "system", "content": system},
325:             {"role": "system", "content": format_instruction},
326:             {"role": "user", "content": user},
327:         ]
328:         messages = list(base_messages)
329:         attempts = self._chat_validation_retries + 1
330:         raw_attempts: list[dict[str, Any]] = []
331:         for attempt in range(attempts):
332:             try:
333:                 with _hard_timeout(self._call_timeout_seconds):
334:                     response = self._client.chat.completions.create(
335:                         model=self._model,
336:                         messages=messages,
337:                         response_format={"type": "json_object"},
338:                         max_tokens=self._max_tokens,
339:                     )
340:             except Exception as exc:
341:                 self.last_raw_response = {
342:                     "provider": "chat.completions",
343:                     "model": self._model,
344:                     "response_model": response_model.__name__,
345:                     "attempts": raw_attempts,
346:                     "request_error": str(exc),
347:                 }
348:                 raise _wrap_provider_exception(
349:                     prefix="OpenAI-compatible request failed",
350:                     response_model=response_model,
351:                     exc=exc,
352:                 ) from exc
353:             self._record_usage(getattr(response, "usage", None))
354: 
355:             choice = response.choices[0]
356:             finish_reason = getattr(choice, "finish_reason", None)
357:             content = choice.message.content
358:             raw_attempt: dict[str, Any] = {
359:                 "attempt": attempt + 1,
360:                 "finish_reason": finish_reason,
361:                 "content": content,
362:             }
363:             usage = getattr(response, "usage", None)
364:             if usage is not None:
365:                 raw_attempt["usage"] = {
366:                     "prompt_tokens": getattr(usage, "prompt_tokens", None),
367:                     "completion_tokens": getattr(usage, "completion_tokens", None),
368:                     "total_tokens": getattr(usage, "total_tokens", None),
369:                 }
370:             raw_attempts.append(raw_attempt)
371:             self.last_raw_response = {
372:                 "provider": "chat.completions",
373:                 "model": self._model,
374:                 "response_model": response_model.__name__,
375:                 "attempts": raw_attempts,
376:             }
377:             if finish_reason == "length":
378:                 raise LLMResponseError(
379:                     f"OpenAI-compatible response was truncated while generating {response_model.__name__}"
380:                 )
381:             if not content:
382:                 if attempt >= attempts - 1:
383:                     raise LLMResponseError(
384:                         f"OpenAI-compatible provider returned no content for {response_model.__name__}"
385:                     )
386:                 repair_instruction = (
387:                     "The previous response had no content."
388:                 )
389:                 messages = self._repair_messages(
390:                     system=system,
391:                     user=user,
392:                     response_model=response_model,
393:                     schema=schema,
394:                     top_level_keys=top_level_keys,
395:                     issue=repair_instruction,
396:                     previous_response="",
397:                 )
398:                 continue
399:             try:
400:                 parsed = _load_json_object_from_text(content)
401:             except json.JSONDecodeError as exc:
402:                 raw_attempt["json_error"] = str(exc)
403:                 if attempt >= attempts - 1:
404:                     raise LLMResponseError(
405:                         f"OpenAI-compatible provider returned invalid JSON for {response_model.__name__}: {exc}",
406:                     ) from exc
407:                 messages = self._repair_messages(
408:                     system=system,
409:                     user=user,
410:                     response_model=response_model,
411:                     schema=schema,
412:                     top_level_keys=top_level_keys,
413:                     issue=f"The previous response was invalid JSON.\nJSON parse error:\n{exc}",
414:                     previous_response=content,
415:                 )
416:                 continue
417:             try:
418:                 result = response_model.model_validate(parsed)
419:                 raw_attempt["validated"] = True
420:                 self.last_raw_response = {
421:                     "provider": "chat.completions",
422:                     "model": self._model,
423:                     "response_model": response_model.__name__,
424:                     "attempts": raw_attempts,
425:                     "validated_json": parsed,
426:                 }
427:                 return result
428:             except ValidationError as exc:
429:                 raw_attempt["validation_error"] = str(exc)
430:                 if attempt >= attempts - 1:
431:                     raise LLMResponseError(
432:                         "OpenAI-compatible provider returned JSON that failed "
433:                         f"schema validation for {response_model.__name__}: {exc}",
434:                     ) from exc
435:                 messages = self._repair_messages(
436:                     system=system,
437:                     user=user,
438:                     response_model=response_model,
439:                     schema=schema,
440:                     top_level_keys=top_level_keys,
441:                     issue=f"The previous JSON failed validation.\nValidation error:\n{exc}",
442:                     previous_response=content,
443:                 )
444:         raise LLMResponseError(
445:             f"OpenAI-compatible provider failed to generate {response_model.__name__}"
```

## File: `src/novel_drama_engine/models.py`
### Lines 345-375
```
345: class EpisodeSourcePacket(BaseModel):
346:     episode: int = Field(ge=1)
347:     source_anchor: str
348:     source_excerpt: str
349:     c0_facts: list[str] = Field(default_factory=list)
350:     c1_must_keep_assets: list[str] = Field(default_factory=list)
351:     source_evidence_assets: list[str] | None = None
352:     c2_visual_assets: list[str] = Field(default_factory=list)
353:     c3_compress_assets: list[str] = Field(default_factory=list)
354:     c4_forbidden_additions: list[str] = Field(default_factory=list)
355:     golden_lines: list[str] = Field(default_factory=list)
356:     active_party: str | None = None
357:     key_decision_timing: str | None = None
358:     handoff_requirement: str | None = None
359: 
360: 
361: class EpisodeSourcePackets(BaseModel):
362:     packets: list[EpisodeSourcePacket] = Field(min_length=1, max_length=5)
363: 
364: 
365: class EpisodeHandoff(BaseModel):
366:     previous_episode: int = Field(ge=1)
367:     previous_title: str
368:     previous_cliffhanger: str
369:     previous_final_lines: list[str] = Field(default_factory=list)
370:     previous_state_update: dict[str, Any] = Field(default_factory=dict)
371: 
372: 
373: SHOT_SIZE_OPENERS = ("全景", "中景", "中近景", "近景", "特写", "俯拍", "仰拍", "长焦")
374: SHOT_MOTION_OPENERS = (
375:     "推近",
```
### Lines 785-920
```
785: 
786:     @model_validator(mode="before")
787:     @classmethod
788:     def wrap_provider_episode_array(cls, data: object) -> object:
789:         if isinstance(data, list):
790:             return {"episodes": data}
791:         return data
792: 
793: 
794: class QualityScores(BaseModel):
795:     hook: int = Field(ge=0, le=10)
796:     conflict: int = Field(ge=0, le=10)
797:     cliffhanger: int = Field(ge=0, le=10)
798:     continuity: int = Field(ge=0, le=10)
799:     video_feasibility: int = Field(ge=0, le=10)
800: 
801: 
802: class QualityReport(BaseModel):
803:     status: QualityStatus
804:     scores: QualityScores
805:     blocking_issues: list[str]
806:     rewrite_instruction: str
807: 
808: 
809: class DramaQualityDimension(BaseModel):
810:     name: Literal[
811:         "character_integrity",
812:         "conflict_causality",
813:         "emotional_progression",
814:         "dialogue_naturalness",
815:         "source_asset_preservation",
816:         "hook_and_cliffhanger",
817:     ]
818:     score: int = Field(ge=0, le=10)
819:     status: Literal["passed", "advisory", "blocking"]
820:     evidence: list[str] = Field(default_factory=list)
821:     suggestion: str = ""
822: 
823: 
824: class DramaQualityComparison(BaseModel):
825:     baseline_overall_score: int = Field(ge=0, le=10)
826:     pipeline_overall_score: int = Field(ge=0, le=10)
827:     delta: int
828:     verdict: Literal[
829:         "pipeline_clearly_better",
830:         "pipeline_slightly_better",
831:         "tie",
832:         "baseline_better",
833:     ]
834:     reason: str
835: 
836: 
837: class DramaQualityReport(BaseModel):
838:     overall_score: int = Field(ge=0, le=10)
839:     dimensions: list[DramaQualityDimension] = Field(default_factory=list)
840:     blocking_issues: list[str] = Field(default_factory=list)
841:     advisory_warnings: list[str] = Field(default_factory=list)
842:     rewrite_instruction: str = ""
843:     baseline_comparison: DramaQualityComparison | None = None
844: 
845: 
846: class EpisodeNoveltyProfile(BaseModel):
847:     episode: int = Field(ge=1)
848:     title: str
849:     scene_skeleton: str
850:     action_signature: str
851:     dialogue_signature: str
852:     cliffhanger_signature: str
853: 
854: 
855: class CrossEpisodeSimilarityIssue(BaseModel):
856:     episodes: tuple[int, int]
857:     kind: Literal[
858:         "overall",
859:         "scene_skeleton",
860:         "action_chain",
861:         "dialogue_pattern",
862:         "cliffhanger",
863:     ]
864:     score: float = Field(ge=0.0, le=1.0)
865:     severity: Literal["blocking", "advisory"]
866:     evidence: list[str] = Field(default_factory=list)
867:     suggestion: str = ""
868: 
869: 
870: class ScriptNoveltyReport(BaseModel):
871:     overall_score: int = Field(ge=0, le=10)
872:     episode_profiles: list[EpisodeNoveltyProfile] = Field(default_factory=list)
873:     similarity_issues: list[CrossEpisodeSimilarityIssue] = Field(default_factory=list)
874:     blocking_issues: list[str] = Field(default_factory=list)
875:     advisory_warnings: list[str] = Field(default_factory=list)
876:     rewrite_instruction: str = ""
877: 
878: 
879: class SourceEvidenceSpan(BaseModel):
880:     asset: str
881:     source_anchor: str
882:     source_excerpt: str
883:     source_line: str | None = None
884:     source_line_index: int | None = Field(default=None, ge=1)
885:     script_line: str | None = None
886:     script_line_index: int | None = Field(default=None, ge=1)
887:     adaptation_reason: str
888:     status: Literal["matched", "missing"]
889: 
890: 
891: class SourceEvidenceItem(BaseModel):
892:     episode: int = Field(ge=1)
893:     source_anchor: str
894:     adaptation_reason: str
895:     retained_assets: list[str] = Field(default_factory=list)
896:     script_evidence: list[str] = Field(default_factory=list)
897:     evidence_spans: list[SourceEvidenceSpan] = Field(default_factory=list)
898:     status: Literal["matched", "partial", "missing"]
899: 
900: 
901: class SourceEvidenceReport(BaseModel):
902:     coverage_score: int = Field(ge=0, le=100)
903:     items: list[SourceEvidenceItem] = Field(default_factory=list)
904:     missing_items: list[str] = Field(default_factory=list)
905:     rewrite_instruction: str = ""
906: 
907: 
908: class CurrentEpisodeRepairPacket(BaseModel):
909:     episode: int = Field(ge=1)
910:     repair_mode: Literal[
911:         "format_patch",
912:         "ending_hook_patch",
913:         "creative_episode_repair",
914:         "full_episode_rewrite",
915:     ]
916:     baseline_policy: str
917:     baseline_episode_text: str
918:     allowed_change_scope: str
919:     editable_targets: list[str] = Field(default_factory=list)
920:     source_evidence_targets: list[str] = Field(default_factory=list)
```
### Lines 984-1075
```
984: class SourceFidelityCheck(BaseModel):
985:     category: Literal[
986:         "C0_immutable_fact",
987:         "C1_must_keep_scene",
988:         "C2_visual_asset",
989:         "C4_forbidden_addition",
990:         "hook_preservation",
991:         "opening_tension_preservation",
992:         "intent_drift",
993:         "agency_ramp",
994:         "support_role_boundary",
995:         "opponent_agency",
996:         "character_integrity",
997:         "source_mapping",
998:         "source_mapping_required",
999:         "source_mapping_context",
1000:     ]
1001:     anchor: str
1002:     status: Literal["passed", "advisory", "blocking"]
1003:     episode: int | None = None
1004:     evidence: list[str] = Field(default_factory=list)
1005:     warning: str | None = None
1006: 
1007: 
1008: class SourceFidelityReport(BaseModel):
1009:     score: int = Field(ge=0, le=100)
1010:     preserved_original_hook: bool
1011:     checks: list[SourceFidelityCheck] = Field(default_factory=list)
1012:     blocking_warnings: list[str] = Field(default_factory=list)
1013:     advisory_warnings: list[str] = Field(default_factory=list)
1014: 
1015: 
1016: class ContinuityLinkReport(BaseModel):
1017:     previous_episode: int
1018:     next_episode: int
1019:     previous_cliffhanger: str
1020:     next_opening: str
1021:     status: Literal["passed", "advisory", "blocking"]
1022:     warnings: list[str] = Field(default_factory=list)
1023: 
1024: 
1025: class ContinuityAuditReport(BaseModel):
1026:     score: int = Field(ge=0, le=100)
1027:     links: list[ContinuityLinkReport] = Field(default_factory=list)
1028:     blocking_warnings: list[str] = Field(default_factory=list)
1029:     advisory_warnings: list[str] = Field(default_factory=list)
1030: 
1031: 
1032: class StoryStateEntry(BaseModel):
1033:     episode: int | None = None
1034:     kind: Literal[
1035:         "open_hook",
1036:         "forbidden_reveal",
1037:         "character_knowledge",
1038:         "relationship_change",
1039:         "prop_state",
1040:         "foreshadowing",
1041:         "episode_state",
1042:         "story_event",
1043:     ]
1044:     key: str
1045:     value: str
1046:     status: Literal["open", "active", "closed", "forbidden"] = "active"
1047:     source: str | None = None
1048: 
1049: 
1050: class StoryStateLedger(BaseModel):
1051:     current_episode: int = Field(ge=0)
1052:     entries: list[StoryStateEntry] = Field(default_factory=list)
1053:     open_hooks: list[str] = Field(default_factory=list)
1054:     forbidden_reveals: list[str] = Field(default_factory=list)
1055:     character_knowledge: dict[str, list[str]] = Field(default_factory=dict)
1056:     relationship_changes: list[str] = Field(default_factory=list)
1057:     prop_states: list[str] = Field(default_factory=list)
1058:     foreshadowing_ledger: list[str] = Field(default_factory=list)
1059:     blocking_warnings: list[str] = Field(default_factory=list)
1060:     warnings: list[str] = Field(default_factory=list)
1061: 
1062: 
1063: class AdaptationQualityReport(BaseModel):
1064:     source_fidelity: SourceFidelityReport
1065:     continuity: ContinuityAuditReport
1066:     story_state_ledger: StoryStateLedger
1067:     blocking_warnings: list[str] = Field(default_factory=list)
1068:     advisory_warnings: list[str] = Field(default_factory=list)
1069:     rewrite_instruction: str = ""
1070: 
1071: 
1072: class RoundResult(BaseModel):
1073:     project_id: str
1074:     round_number: int = Field(ge=1)
1075:     source_analysis: SourceAnalysis
```

## File: `tests/test_pipeline.py`
### Lines 1030-1105
```
1030:         context,
1031:         bible,
1032:         weak_script,
1033:         None,
1034:     )
1035: 
1036:     assert report.status == QualityStatus.NEEDS_REWRITE
1037:     assert any("too short" in issue for issue in report.blocking_issues)
1038:     assert "双层质检" in report.rewrite_instruction
1039: 
1040: 
1041: def test_pipeline_default_repair_targets_episode_without_batch_rewrite(
1042:     tmp_path,
1043:     happy_round_outputs,
1044: ):
1045:     outputs = list(happy_round_outputs)
1046:     first_script = outputs[3]
1047:     failed_quality = QualityReport(
1048:         status=QualityStatus.NEEDS_REWRITE,
1049:         scores=QualityScores(
1050:             hook=4,
1051:             conflict=6,
1052:             cliffhanger=5,
1053:             continuity=9,
1054:             video_feasibility=8,
1055:         ),
1056:         blocking_issues=["前3秒 Hook 不够强"],
1057:         rewrite_instruction="EP01 前3秒 Hook 不够强，只修第一集开头。",
1058:     )
1059:     repaired_episode = first_script.episodes[0].model_copy(
1060:         deep=True,
1061:         update={"hook_3s": "把她拖出去！她不是林家的女儿！"},
1062:     )
1063:     final_quality = QualityReport(
1064:         status=QualityStatus.USABLE,
1065:         scores=QualityScores(
1066:             hook=9,
1067:             conflict=9,
1068:             cliffhanger=8,
1069:             continuity=10,
1070:             video_feasibility=8,
1071:         ),
1072:         blocking_issues=[],
1073:         rewrite_instruction="",
1074:     )
1075:     outputs = outputs[:4] + [failed_quality, repaired_episode, final_quality, outputs[5]]
1076:     llm = RecordingLLM(outputs)
1077:     pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))
1078: 
1079:     result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")
1080: 
1081:     script_calls = [
1082:         call
1083:         for call in llm.calls
1084:         if call["response_model"].__name__ == "ScriptBatch"
1085:     ]
1086:     episode_calls = [
1087:         call
1088:         for call in llm.calls
1089:         if call["response_model"].__name__ == "EpisodeScript"
1090:     ]
1091:     assert result.script_batch.episodes[0].hook_3s == "把她拖出去！她不是林家的女儿！"
1092:     assert result.script_batch.episodes[1] == first_script.episodes[1]
1093:     assert result.quality_report.status == QualityStatus.USABLE
1094:     assert len(script_calls) == 1
1095:     assert len(episode_calls) == 1
1096:     assert failed_quality.rewrite_instruction not in script_calls[0]["user"]
1097:     assert failed_quality.rewrite_instruction in episode_calls[0]["user"]
1098:     assert "current_episode_repair_packet" in episode_calls[0]["user"]
1099:     assert "当前集旧稿是唯一文本基准" in episode_calls[0]["user"]
1100:     assert "baseline_episode_text" in episode_calls[0]["user"]
1101:     assert (tmp_path / "round_001" / "quality_report_before_rewrite.json").exists()
1102:     assert (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()
1103:     repair_packets = json.loads(
1104:         (tmp_path / "round_001" / "current_episode_repair_packets.json").read_text(
1105:             encoding="utf-8"
```
### Lines 1450-1610
```
1450:             continuity=9,
1451:             video_feasibility=8,
1452:         ),
1453:         blocking_issues=["Hook 太弱"],
1454:         rewrite_instruction="强化前3秒冲突。",
1455:     )
1456:     second_quality = QualityReport(
1457:         status=QualityStatus.NEEDS_REWRITE,
1458:         scores=QualityScores(
1459:             hook=5,
1460:             conflict=6,
1461:             cliffhanger=5,
1462:             continuity=9,
1463:             video_feasibility=8,
1464:         ),
1465:         blocking_issues=["逐集修复后仍缺少镜头密度"],
1466:         rewrite_instruction="需要人工重构。",
1467:     )
1468:     llm = RecordingLLM(
1469:         outputs[:4] + [first_quality, repaired_episode, second_quality, outputs[5]]
1470:     )
1471:     pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))
1472: 
1473:     result = pipeline.run(
1474:         project_id="demo",
1475:         round_number=1,
1476:         source_text="林晚被赶出生日宴。",
1477:         repair_budget="episode",
1478:     )
1479: 
1480:     script_calls = [
1481:         call
1482:         for call in llm.calls
1483:         if call["response_model"].__name__ == "ScriptBatch"
1484:     ]
1485:     episode_repair_calls = [
1486:         call
1487:         for call in llm.calls
1488:         if call["response_model"].__name__ == "EpisodeScript"
1489:     ]
1490:     quality_path = tmp_path / "round_001" / "quality_report.json"
1491:     assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
1492:     assert len(script_calls) == 1
1493:     assert len(episode_repair_calls) == 1
1494:     assert "needs_human_review" in quality_path.read_text(encoding="utf-8")
1495:     assert (tmp_path / "round_001" / "round_result.json").exists()
1496:     assert (tmp_path / "round_001" / "next_round_context.json").exists()
1497:     assert (tmp_path / "round_001" / "quality_report_before_episode_repair.json").exists()
1498:     assert (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()
1499: 
1500: 
1501: def test_pipeline_episode_repair_targets_reported_episode_only(
1502:     tmp_path,
1503:     happy_round_outputs,
1504: ):
1505:     outputs = list(happy_round_outputs)
1506:     first_script = outputs[3]
1507:     repaired_episode = first_script.episodes[0].model_copy(
1508:         deep=True,
1509:         update={"title": "定向修复第一集"},
1510:     )
1511:     first_quality = QualityReport(
1512:         status=QualityStatus.NEEDS_REWRITE,
1513:         scores=QualityScores(
1514:             hook=3,
1515:             conflict=5,
1516:             cliffhanger=4,
1517:             continuity=9,
1518:             video_feasibility=8,
1519:         ),
1520:         blocking_issues=["EP01 镜头密度仍不足"],
1521:         rewrite_instruction="只重修 EP01，其他集保持边界不变。",
1522:     )
1523:     final_quality = QualityReport(
1524:         status=QualityStatus.USABLE,
1525:         scores=QualityScores(
1526:             hook=9,
1527:             conflict=9,
1528:             cliffhanger=9,
1529:             continuity=9,
1530:             video_feasibility=8,
1531:         ),
1532:         blocking_issues=[],
1533:         rewrite_instruction="",
1534:     )
1535:     llm = RecordingLLM(outputs[:4] + [first_quality, repaired_episode, final_quality, outputs[5]])
1536:     pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))
1537: 
1538:     result = pipeline.run(
1539:         project_id="demo",
1540:         round_number=1,
1541:         source_text="林晚被赶出生日宴。",
1542:         repair_budget="episode",
1543:     )
1544: 
1545:     episode_repair_calls = [
1546:         call
1547:         for call in llm.calls
1548:         if call["response_model"].__name__ == "EpisodeScript"
1549:     ]
1550:     target_text = (tmp_path / "round_001" / "episode_repair_targets.md").read_text(
1551:         encoding="utf-8"
1552:     )
1553:     assert len(episode_repair_calls) == 1
1554:     assert result.script_batch.episodes[0].title == "定向修复第一集"
1555:     assert result.script_batch.episodes[1] == first_script.episodes[1]
1556:     assert target_text == "EP01"
1557: 
1558: 
1559: def test_quality_instruction_for_episode_excludes_other_episode_failures():
1560:     quality_report = QualityReport(
1561:         status=QualityStatus.NEEDS_REWRITE,
1562:         scores=QualityScores(
1563:             hook=4,
1564:             conflict=5,
1565:             cliffhanger=4,
1566:             continuity=8,
1567:             video_feasibility=8,
1568:         ),
1569:         blocking_issues=[
1570:             "EP01 too short: 664 chars, expected >= 800",
1571:             "EP02 has non-shooting scene headings: 2-1 白-内-林挽清公寓",
1572:             "source_evidence: EP05 缺少原文资产：雪地烟火激吻",
1573:             "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。",
1574:         ],
1575:         rewrite_instruction=(
1576:             "方法论阻断：本素材被判定为强原文，只允许轻改；"
1577:             "EP01 has 8 action lines, expected >= 10；"
1578:             "EP02 too short: 660 chars, expected >= 800；"
1579:             "The provided scripts accurately map to the source. No blocking issues detected."
1580:         ),
1581:     )
1582: 
1583:     scoped = quality_instruction_for_episode(quality_report, 1)
1584: 
1585:     assert "方法论阻断" in scoped
1586:     assert "EP01 too short" in scoped
1587:     assert "EP01 has 8 action lines" in scoped
1588:     assert "source_asset_preservation" in scoped
1589:     assert "EP02" not in scoped
1590:     assert "EP05" not in scoped
1591:     assert "雪地烟火激吻" not in scoped
1592:     assert "No blocking issues detected" not in scoped
1593: 
1594: 
1595: def test_pipeline_polishes_episode_repair_when_local_quality_still_fails(
1596:     tmp_path,
1597:     happy_round_outputs,
1598:     monkeypatch,
1599: ):
1600:     monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
1601:     monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
1602:     outputs = list(happy_round_outputs)
1603:     first_script = outputs[3]
1604:     bad_episode = first_script.episodes[0].model_copy(
1605:         deep=True,
1606:         update={
1607:             "scenes": [
1608:                 Scene(
1609:                     heading="1-1 夜-内-温家走廊",
1610:                     characters=["林晚", "温舟"],
```
### Lines 1830-2020
```
1830: ):
1831:     monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
1832:     monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
1833:     outputs = list(happy_round_outputs)
1834:     first_script = outputs[3]
1835:     soft_tail_episode = first_script.episodes[0].model_copy(deep=True)
1836:     soft_tail_episode.cliffhanger = "明天再说。"
1837:     soft_tail_episode.scenes[-1].lines[-2:] = [
1838:         SceneLine(kind="dialogue", speaker="林晚", text="明天再说。"),
1839:         SceneLine(kind="action", text="△中景林晚转身离开。"),
1840:     ]
1841:     first_quality = QualityReport(
1842:         status=QualityStatus.NEEDS_REWRITE,
1843:         scores=QualityScores(
1844:             hook=3,
1845:             conflict=5,
1846:             cliffhanger=4,
1847:             continuity=9,
1848:             video_feasibility=8,
1849:         ),
1850:         blocking_issues=["Hook 太弱"],
1851:         rewrite_instruction="强化前3秒冲突。",
1852:     )
1853:     final_quality = QualityReport(
1854:         status=QualityStatus.USABLE,
1855:         scores=QualityScores(
1856:             hook=9,
1857:             conflict=9,
1858:             cliffhanger=9,
1859:             continuity=9,
1860:             video_feasibility=8,
1861:         ),
1862:         blocking_issues=[],
1863:         rewrite_instruction="",
1864:     )
1865:     llm = RecordingLLM(
1866:         outputs[:4]
1867:         + [first_quality, soft_tail_episode, soft_tail_episode, first_script.episodes[0], final_quality, outputs[5]]
1868:     )
1869:     pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))
1870: 
1871:     result = pipeline.run(
1872:         project_id="demo",
1873:         round_number=1,
1874:         source_text="林晚被赶出生日宴。",
1875:         repair_budget="episode",
1876:     )
1877: 
1878:     episode_calls = [
1879:         call
1880:         for call in llm.calls
1881:         if call["response_model"].__name__ == "EpisodeScript"
1882:     ]
1883:     assert result.quality_report.status == QualityStatus.USABLE
1884:     assert len(episode_calls) == 3
1885:     assert "结尾钩子/对白密度二次编译" in episode_calls[-1]["user"]
1886:     assert "不要整集重写" in episode_calls[-1]["user"]
1887:     assert (tmp_path / "round_001" / "hook_dialogue_polish_instructions.md").exists()
1888:     assert (tmp_path / "round_001" / "script_batch_hook_dialogue_polish.json").exists()
1889: 
1890: 
1891: def test_pipeline_keeps_quality_polished_episode_when_hook_polish_fails(
1892:     tmp_path,
1893:     happy_round_outputs,
1894:     monkeypatch,
1895: ):
1896:     monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
1897:     monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
1898:     outputs = list(happy_round_outputs)
1899:     first_script = outputs[3]
1900:     soft_tail_episode = first_script.episodes[0].model_copy(deep=True)
1901:     soft_tail_episode.cliffhanger = "明天再说。"
1902:     soft_tail_episode.scenes[-1].lines[-2:] = [
1903:         SceneLine(kind="dialogue", speaker="林晚", text="明天再说。"),
1904:         SceneLine(kind="action", text="△中景林晚转身离开。"),
1905:     ]
1906:     first_quality = QualityReport(
1907:         status=QualityStatus.NEEDS_REWRITE,
1908:         scores=QualityScores(
1909:             hook=3,
1910:             conflict=5,
1911:             cliffhanger=4,
1912:             continuity=9,
1913:             video_feasibility=8,
1914:         ),
1915:         blocking_issues=["Hook 太弱"],
1916:         rewrite_instruction="强化前3秒冲突。",
1917:     )
1918:     final_quality = QualityReport(
1919:         status=QualityStatus.USABLE,
1920:         scores=QualityScores(
1921:             hook=9,
1922:             conflict=9,
1923:             cliffhanger=9,
1924:             continuity=9,
1925:             video_feasibility=8,
1926:         ),
1927:         blocking_issues=[],
1928:         rewrite_instruction="",
1929:     )
1930:     llm = RecordingLLM(
1931:         outputs[:4]
1932:         + [first_quality, soft_tail_episode]
1933:         + [
1934:             soft_tail_episode,
1935:             RuntimeError("provider returned scene object"),
1936:             final_quality,
1937:             outputs[5],
1938:         ]
1939:     )
1940:     pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))
1941: 
1942:     result = pipeline.run(
1943:         project_id="demo",
1944:         round_number=1,
1945:         source_text="林晚被赶出生日宴。",
1946:         repair_budget="episode",
1947:     )
1948: 
1949:     assert result.quality_report.status in {
1950:         QualityStatus.USABLE,
1951:         QualityStatus.NEEDS_HUMAN_REVIEW,
1952:     }
1953:     assert result.script_batch.episodes[0] == soft_tail_episode
1954:     assert (tmp_path / "round_001" / "script_batch_hook_dialogue_polish.json").exists()
1955:     assert (tmp_path / "round_001" / "hook_dialogue_polish_failures.md").exists()
1956: 
1957: 
1958: def test_pipeline_default_repair_budget_is_episode():
1959:     assert normalize_repair_budget(None) == RepairBudget.EPISODE
1960: 
1961: 
1962: def test_pipeline_rewrite_repair_budget_skips_episode_repair(tmp_path, happy_round_outputs):
1963:     outputs = list(happy_round_outputs)
1964:     first_script = outputs[3]
1965:     rewritten_script = first_script.model_copy(deep=True)
1966:     first_quality = QualityReport(
1967:         status=QualityStatus.NEEDS_REWRITE,
1968:         scores=QualityScores(
1969:             hook=3,
1970:             conflict=5,
1971:             cliffhanger=4,
1972:             continuity=9,
1973:             video_feasibility=8,
1974:         ),
1975:         blocking_issues=["Hook 太弱"],
1976:         rewrite_instruction="强化前3秒冲突。",
1977:     )
1978:     second_quality = QualityReport(
1979:         status=QualityStatus.NEEDS_REWRITE,
1980:         scores=QualityScores(
1981:             hook=5,
1982:             conflict=5,
1983:             cliffhanger=4,
1984:             continuity=9,
1985:             video_feasibility=8,
1986:         ),
1987:         blocking_issues=["重写后仍缺少爆点"],
1988:         rewrite_instruction="需要人工重构场景。",
1989:     )
1990:     llm = RecordingLLM(
1991:         outputs[:4] + [first_quality, rewritten_script, second_quality, outputs[5]]
1992:     )
1993:     pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))
1994: 
1995:     result = pipeline.run(
1996:         project_id="demo",
1997:         round_number=1,
1998:         source_text="林晚被赶出生日宴。",
1999:         repair_budget="rewrite",
2000:     )
2001: 
2002:     episode_repair_calls = [
2003:         call
2004:         for call in llm.calls
2005:         if call["response_model"].__name__ == "EpisodeScript"
2006:     ]
2007:     assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
2008:     assert episode_repair_calls == []
2009:     assert (tmp_path / "round_001" / "quality_report_before_rewrite.json").exists()
2010:     assert not (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()
2011:     assert result.runtime_report is not None
2012:     assert result.runtime_report.repair_budget == "rewrite"
```

## File: `tests/test_adaptation_quality.py`
### Lines 319-445
```
319: def test_source_fidelity_scores_required_assets_without_treating_actions_as_source():
320:     context = EpisodeContext(
321:         target_episode_range="EP01-EP01",
322:         story_stage=StoryStage.OPENING_PRESSURE,
323:         source_to_episode_mapping=[
324:             {
325:                 "source": "颁奖礼后台羞辱",
326:                 "target_episode": "EP01",
327:                 "retained_assets": "西装手部压迫、包臀裙羞辱、手机短信嘲讽",
328:                 "information_increment": "女主身份、隐藏恋情与背叛危机",
329:                 "adaptation_action": "将内心OS转为紧迫呼吸和局部特写",
330:             }
331:         ],
332:         must_carry_context=[],
333:         forbidden_reveals=[],
334:         adaptation_actions=[],
335:         confidence=0.9,
336:     )
337:     script = EpisodeScript(
338:         episode=1,
339:         title="颁奖台下",
340:         hook_3s="别出声。",
341:         main_emotion="羞辱",
342:         watch_reason="系统内部看点",
343:         scenes=[
344:             Scene(
345:                 heading="1-1 夜-内-颁奖礼后台",
346:                 characters=["林挽清", "路淮北"],
347:                 lines=[
348:                     SceneLine(
349:                         kind="action",
350:                         text="△特写推近路淮北西装手部压迫林挽清，包臀裙羞辱被聚光灯扫到。",
351:                     ),
352:                     SceneLine(kind="dialogue", speaker="路淮北", emotion="低声", text="别出声。"),
353:                 ],
354:             )
355:         ],
356:         cliffhanger="手机在她掌心震动。",
357:         state_update={},
358:     )
359: 
360:     report = build_adaptation_quality_report(
361:         source_text="颁奖礼后台，路淮北用西装手臂压住她，包臀裙被迫皱起，手机后来震动。",
362:         source_analysis=make_source_analysis("别出声。"),
363:         episode_context=context,
364:         story_bible=make_bible(),
365:         script_batch=ScriptBatch(episodes=[script]),
366:         next_round_context=make_next_context(),
367:         previous_context=None,
368:     )
369: 
370:     assert report.source_fidelity.score == 67
371:     assert any(check.category == "source_mapping_required" for check in report.source_fidelity.checks)
372:     assert any(check.category == "source_mapping_context" for check in report.source_fidelity.checks)
373:     assert not any("将内心OS转为" in item for item in report.blocking_warnings)
374: 
375: 
376: def test_source_fidelity_does_not_block_current_round_on_future_episode_assets():
377:     context = EpisodeContext(
378:         target_episode_range="EP01-EP02",
379:         story_stage=StoryStage.OPENING_PRESSURE,
380:         source_to_episode_mapping=[
381:             {
382:                 "source": "颁奖礼后台羞辱",
383:                 "target_episode": "EP01",
384:                 "retained_assets": "路淮北手部压迫、许念念台上领奖",
385:                 "information_increment": "隐藏恋情与背叛危机",
386:                 "adaptation_action": "保留开场压迫",
387:             },
388:             {
389:                 "source": "雪地烟火激吻，照片随后被公开",
390:                 "target_episode": "EP08",
391:                 "retained_assets": "雪地烟火激吻、照片被公开",
392:                 "information_increment": "后续公开关系危机",
393:                 "adaptation_action": "未来轮次承接",
394:             },
395:         ],
396:         must_carry_context=[],
397:         forbidden_reveals=[],
398:         adaptation_actions=[],
399:         confidence=0.9,
400:     )
401:     script = EpisodeScript(
402:         episode=1,
403:         title="颁奖台下",
404:         hook_3s="别出声。",
405:         main_emotion="羞辱",
406:         watch_reason="系统内部看点",
407:         scenes=[
408:             Scene(
409:                 heading="1-1 夜-内-颁奖礼后台",
410:                 characters=["林挽清", "路淮北", "许念念"],
411:                 lines=[
412:                     SceneLine(
413:                         kind="action",
414:                         text="△特写推近路淮北手部压迫林挽清，门缝外许念念台上领奖。",
415:                     ),
416:                     SceneLine(kind="dialogue", speaker="路淮北", emotion="低声", text="别出声。"),
417:                 ],
418:             )
419:         ],
420:         cliffhanger="主持人的声音压过门缝。",
421:         state_update={},
422:     )
423: 
424:     report = build_adaptation_quality_report(
425:         source_text="颁奖礼后台，路淮北压住她。很久之后，雪地烟火下两人接吻，照片被公开。",
426:         source_analysis=make_source_analysis("别出声。"),
427:         episode_context=context,
428:         story_bible=make_bible(),
429:         script_batch=ScriptBatch(episodes=[script]),
430:         next_round_context=make_next_context(),
431:         previous_context=None,
432:     )
433: 
434:     warning_text = "\n".join(report.blocking_warnings)
435:     assert "雪地烟火激吻" not in warning_text
436:     assert "照片被公开" not in warning_text
437: 
438: 
439: def test_forbidden_change_detection_does_not_flag_broad_character_name_overlap():
440:     bible = make_bible()
441:     bible.forbidden_changes = [
442:         "禁止在林挽清对路淮北死心前增加暧昧戏份。",
443:         "严禁将路淮北写出任何洗白情节或苦衷背景。",
444:     ]
445: 
```
### Lines 681-745
```
681:     ledger = build_story_state_ledger(
682:         script_batch=ScriptBatch(episodes=[first, second]),
683:         next_round_context=make_next_context(),
684:         previous_context=None,
685:     )
686: 
687:     first_hook = next(
688:         entry
689:         for entry in ledger.entries
690:         if entry.kind == "open_hook"
691:         and entry.source == "episode.cliffhanger"
692:         and entry.episode == 1
693:     )
694:     assert first_hook.status == "closed"
695:     assert "next_round_context open_hooks does not carry the final episode cliffhanger" in ledger.warnings
696: 
697: 
698: def test_continuity_blocks_forbidden_previous_reveal_leak():
699:     previous_context = make_next_context()
700:     previous_context.forbidden_reveals = ["亲子鉴定完整结果"]
701:     report = build_adaptation_quality_report(
702:         source_text="林晚生日宴被羞辱，旧木盒出现。",
703:         source_analysis=make_source_analysis(),
704:         episode_context=make_context(),
705:         story_bible=make_bible(),
706:         script_batch=ScriptBatch(
707:             episodes=[
708:                 make_episode(
709:                     hook="亲子鉴定完整结果出来了。",
710:                     final="你到底是谁？",
711:                 )
712:             ]
713:         ),
714:         next_round_context=make_next_context(),
715:         previous_context=previous_context,
716:     )
717: 
718:     assert any("forbidden reveal leaked" in item for item in report.blocking_warnings)
719: 
720: 
721: def test_continuity_allows_partial_identity_clue_without_full_reveal():
722:     previous_context = make_next_context()
723:     previous_context.forbidden_reveals = ["林晚是真千金"]
724:     report = build_adaptation_quality_report(
725:         source_text="林晚生日宴被羞辱，旧木盒出现。",
726:         source_analysis=make_source_analysis("谁敢碰她一下！"),
727:         episode_context=make_context(),
728:         story_bible=make_bible(),
729:         script_batch=ScriptBatch(
730:             episodes=[
731:                 make_episode(
732:                     hook="这块玉佩，只有真千金才有。",
733:                     final="她到底是不是林家人？",
734:                 )
735:             ]
736:         ),
737:         next_round_context=make_next_context(),
738:         previous_context=previous_context,
739:     )
740: 
741:     assert not any("forbidden reveal leaked" in item for item in report.blocking_warnings)
742: 
743: 
744: def test_source_fidelity_blocks_passive_promise_rewritten_as_protagonist_demand():
745:     report = build_adaptation_quality_report(
```
### Lines 790-850
```
790:             "她僵住，害怕被颁奖礼镜头拍到。"
791:         ),
792:         source_analysis=make_source_analysis("害怕被颁奖礼镜头拍到"),
793:         episode_context=make_context(),
794:         story_bible=make_bible(),
795:         script_batch=ScriptBatch(
796:             episodes=[
797:                 make_episode(
798:                     hook="颁奖礼开始了。",
799:                     final="名单公布了。",
800:                 )
801:             ]
802:         ),
803:         next_round_context=make_next_context(),
804:         previous_context=None,
805:     )
806: 
807:     assert any("opening tension asset" in item for item in report.blocking_warnings)
808: 
809: 
810: def empty_source_analysis() -> SourceAnalysis:
811:     return SourceAnalysis(
812:         characters=["甲", "乙", "丙"],
813:         events=[],
814:         conflicts=[],
815:         visual_moments=[],
816:         low_value_passages=[],
817:         candidate_hooks=[],
818:     )
819: 
820: 
821: def test_story_event_ledger_blocks_repeated_high_impact_intimacy_exposure():
822:     report = build_adaptation_quality_report(
823:         source_text="公开亲密曝光是单次高价值名场面，后续只能承接后果。",
824:         source_analysis=empty_source_analysis(),
825:         episode_context=EpisodeContext(
826:             target_episode_range="EP05-EP09",
827:             story_stage=StoryStage.MISUNDERSTANDING_ESCALATION,
828:             source_to_episode_mapping=[],
829:             must_carry_context=[],
830:             forbidden_reveals=[],
831:             adaptation_actions=[],
832:             confidence=0.9,
833:         ),
834:         story_bible=make_bible(),
835:         script_batch=ScriptBatch(
836:             episodes=[
837:                 make_episode(
838:                     5,
839:                     hook="订婚宴舞台上，他低头吻住她，直播镜头亮起。",
840:                     final="照片已经上热搜。",
841:                 ),
842:                 make_episode(
843:                     9,
844:                     hook="庆典镜头前，他再次吻住她，偷拍视频曝光。",
845:                     final="全网又炸了。",
846:                 ),
847:             ]
848:         ),
849:         next_round_context=NextRoundContext(
850:             summary="EP09 停在二次曝光。",
```
### Lines 998-1115
```
998:         episode_context=EpisodeContext(
999:             target_episode_range="EP05-EP06",
1000:             story_stage=StoryStage.PUBLIC_REVEAL,
1001:             source_to_episode_mapping=[],
1002:             must_carry_context=[],
1003:             forbidden_reveals=[],
1004:             adaptation_actions=[],
1005:             confidence=0.9,
1006:         ),
1007:         story_bible=make_bible(),
1008:         script_batch=ScriptBatch(
1009:             episodes=[
1010:                 make_plain_episode(
1011:                     5,
1012:                     hook="祖传令牌和鉴定书同时亮出。",
1013:                     final="长老要求当众验证。",
1014:                 ),
1015:                 make_plain_episode(
1016:                     6,
1017:                     hook="全场公开他的真实身份。",
1018:                     final="少主身份终于坐实。",
1019:                 ),
1020:             ]
1021:         ),
1022:         next_round_context=NextRoundContext(
1023:             summary="EP06 身份公开。",
1024:             current_episode=6,
1025:             open_hooks=["少主身份终于坐实。"],
1026:             forbidden_reveals=[],
1027:             character_knowledge={},
1028:             relationship_changes=[],
1029:             prop_states=["祖传令牌和鉴定书已公开"],
1030:             foreshadowing_ledger=[],
1031:         ),
1032:         previous_context=None,
1033:     )
1034: 
1035:     assert not any("身份/真相结论公开" in item for item in report.blocking_warnings)
1036: 
1037: 
1038: def character_agency_source_analysis() -> SourceAnalysis:
1039:     return SourceAnalysis(
1040:         characters=["主角", "对手", "支持者"],
1041:         events=["主角在公开压迫中僵住，随后逐步清醒"],
1042:         conflicts=["主角被对手持续压迫"],
1043:         visual_moments=[],
1044:         low_value_passages=[],
1045:         candidate_hooks=[],
1046:     )
1047: 
1048: 
1049: def character_agency_bible() -> StoryBible:
1050:     return StoryBible(
1051:         genre="通用强冲突短剧",
1052:         mainline="主角在压迫中逐步清醒并反击。",
1053:         characters=["主角", "对手", "支持者"],
1054:         relationships=["对手持续压迫主角", "支持者给主角后盾"],
1055:         speech_styles={"主角": "克制短句", "对手": "直白施压", "支持者": "短句给后盾"},
1056:         immutable_facts=["主角经历公开压迫"],
1057:         forbidden_changes=["不得让支持者替主角完成核心决定"],
1058:     )
1059: 
1060: 
1061: def test_source_fidelity_blocks_early_omniscient_counterattack_when_source_is_vulnerable():
1062:     report = build_adaptation_quality_report(
1063:         source_text="开场主角被公开羞辱，僵住，手指发抖。她没有立刻反击，只是在心碎后逐步清醒。",
1064:         source_analysis=character_agency_source_analysis(),
1065:         episode_context=make_context(),
1066:         story_bible=character_agency_bible(),
1067:         script_batch=ScriptBatch(
1068:             episodes=[
1069:                 make_plain_episode(
1070:                     1,
1071:                     hook="我早就知道你们完了。",
1072:                     final="所有证据都在我手里。",
1073:                 )
1074:             ]
1075:         ),
1076:         next_round_context=make_next_context(),
1077:         previous_context=None,
1078:     )
1079: 
1080:     assert any("全知全能式开杀" in item for item in report.blocking_warnings)
1081:     assert any(check.category == "agency_ramp" for check in report.source_fidelity.checks)
1082: 
1083: 
1084: def test_source_fidelity_allows_omniscient_counterattack_when_source_has_preexisting_power():
1085:     report = build_adaptation_quality_report(
1086:         source_text="主角重生归来，早就知道对手设局，也提前布好证据。她曾被羞辱，这一次要主动破局。",
1087:         source_analysis=character_agency_source_analysis(),
1088:         episode_context=make_context(),
1089:         story_bible=character_agency_bible(),
1090:         script_batch=ScriptBatch(
1091:             episodes=[
1092:                 make_plain_episode(
1093:                     1,
1094:                     hook="我早就知道你们完了。",
1095:                     final="所有证据都在我手里。",
1096:                 )
1097:             ]
1098:         ),
1099:         next_round_context=make_next_context(),
1100:         previous_context=None,
1101:     )
1102: 
1103:     assert not any("全知全能式开杀" in item for item in report.blocking_warnings)
1104: 
1105: 
1106: def test_source_fidelity_blocks_support_role_taking_over_protagonist_choice():
1107:     report = build_adaptation_quality_report(
1108:         source_text="主角必须自己做离开决定，支持者只能递证据和兜底。",
1109:         source_analysis=character_agency_source_analysis(),
1110:         episode_context=make_context(),
1111:         story_bible=character_agency_bible(),
1112:         script_batch=ScriptBatch(
1113:             episodes=[
1114:                 make_plain_episode(
1115:                     1,
```

## File: `tests/test_source_evidence.py`
### Lines 150-290
```
150:     packets = EpisodeSourcePackets(
151:         packets=[
152:             EpisodeSourcePacket(
153:                 episode=1,
154:                 source_anchor="原文里亲哥哥突然救场。",
155:                 source_excerpt="林晚被赶出时，亲哥哥突然出现。",
156:                 c1_must_keep_assets=["亲哥哥救场"],
157:             )
158:         ]
159:     )
160:     source_evidence_report = build_source_evidence_report(
161:         script_batch,
162:         episode_source_packets=packets,
163:     )
164:     quality_report = QualityReport(
165:         status=QualityStatus.USABLE,
166:         scores=QualityScores(
167:             hook=9,
168:             conflict=9,
169:             cliffhanger=9,
170:             continuity=9,
171:             video_feasibility=9,
172:         ),
173:         blocking_issues=[],
174:         rewrite_instruction="",
175:     )
176: 
177:     merged = merge_source_evidence_into_quality_report(
178:         quality_report,
179:         source_evidence_report,
180:     )
181: 
182:     assert merged.status == QualityStatus.NEEDS_REWRITE
183:     assert any(issue.startswith("source_evidence:") for issue in merged.blocking_issues)
184:     assert "亲哥哥救场" in merged.rewrite_instruction
185: 
186: 
187: def test_source_evidence_scores_each_asset_not_only_episode_hit():
188:     packet = EpisodeSourcePacket(
189:         episode=1,
190:         source_anchor="颁奖礼后台羞辱",
191:         source_excerpt="林挽清被藏在后台，路淮北把手探进她礼服。许念念在台上举起奖杯。",
192:         c1_must_keep_assets=["路淮北把手探进她礼服", "许念念在台上举起奖杯"],
193:     )
194:     script = EpisodeScript(
195:         episode=1,
196:         title="后台羞辱",
197:         hook_3s="别出声。",
198:         main_emotion="压迫",
199:         watch_reason="系统内部看点",
200:         scenes=[
201:             Scene(
202:                 heading="1-1 夜-内-颁奖礼后台",
203:                 characters=["林挽清", "路淮北"],
204:                 lines=[
205:                     SceneLine(
206:                         kind="action",
207:                         text="△特写推近路淮北的手探进林挽清礼服腰侧，舞台掌声从门缝灌进来。",
208:                     ),
209:                     SceneLine(kind="dialogue", speaker="路淮北", emotion="低声", text="别出声。"),
210:                 ],
211:             )
212:         ],
213:         cliffhanger="别出声。",
214:         state_update={},
215:     )
216: 
217:     report = build_source_evidence_report(
218:         ScriptBatch(episodes=[script]),
219:         episode_source_packets=EpisodeSourcePackets(packets=[packet]),
220:     )
221: 
222:     assert report.coverage_score == 50
223:     assert report.items[0].status == "partial"
224:     assert any("许念念在台上举起奖杯" in item for item in report.missing_items)
225:     assert len(report.items[0].evidence_spans) == 2
226:     assert [span.status for span in report.items[0].evidence_spans] == [
227:         "matched",
228:         "missing",
229:     ]
230: 
231: 
232: def test_source_evidence_skips_packets_without_current_episode_script():
233:     script = EpisodeScript(
234:         episode=1,
235:         title="颁奖台下",
236:         hook_3s="别出声。",
237:         main_emotion="羞辱",
238:         watch_reason="系统内部看点",
239:         scenes=[
240:             Scene(
241:                 heading="1-1 夜-内-颁奖礼后台",
242:                 characters=["林挽清", "路淮北"],
243:                 lines=[
244:                     SceneLine(
245:                         kind="action",
246:                         text="△特写推近路淮北手部压迫林挽清，门缝外掌声涌进来。",
247:                     )
248:                 ],
249:             )
250:         ],
251:         cliffhanger="主持人的声音压过门缝。",
252:         state_update={},
253:     )
254:     packets = EpisodeSourcePackets(
255:         packets=[
256:             EpisodeSourcePacket(
257:                 episode=8,
258:                 source_anchor="雪地烟火激吻，照片随后被公开。",
259:                 source_excerpt="雪地烟火下两人接吻，照片被公开。",
260:                 source_evidence_assets=["雪地烟火激吻", "照片被公开"],
261:             )
262:         ]
263:     )
264: 
265:     report = build_source_evidence_report(
266:         ScriptBatch(episodes=[script]),
267:         episode_source_packets=packets,
268:     )
269: 
270:     assert report.coverage_score == 100
271:     assert report.items == []
272:     assert report.missing_items == []
273:     assert report.rewrite_instruction == ""
274: 
275: 
276: def test_source_evidence_does_not_block_on_visual_methodology_actions():
277:     packet = EpisodeSourcePacket(
278:         episode=1,
279:         source_anchor="颁奖礼后台羞辱",
280:         source_excerpt="林挽清被藏在后台，路淮北把手探进她礼服。",
281:         c1_must_keep_assets=["路淮北把手探进她礼服"],
282:         c2_visual_assets=[
283:             "将内心OS转为紧迫的呼吸动作与镜头的局部特写，强化被公开处刑的耻辱感"
284:         ],
285:     )
286:     script = EpisodeScript(
287:         episode=1,
288:         title="后台羞辱",
289:         hook_3s="别出声。",
290:         main_emotion="压迫",
```

## File: `tests/test_script_quality.py`
### Lines 160-210
```
160:     assert episode_repair_mode(episode) == "full_episode_rewrite"
161:     assert (
162:         episode_repair_mode(
163:             episode,
164:             "强原文轻改：当前集只能基于原文当前集做最小修复。",
165:             allow_full_rewrite=False,
166:         )
167:         == "creative_episode_repair"
168:     )
169: 
170: 
171: def test_light_edit_current_episode_repair_packet_forbids_full_rewrite():
172:     episode = EpisodeScript(
173:         episode=1,
174:         title="强原文轻改短稿",
175:         hook_3s="她把规矩纸折进兜里。",
176:         main_emotion="克制",
177:         watch_reason="观众要看她如何借原文冲突反击。",
178:         scenes=[
179:             Scene(
180:                 heading="1-1 早-内-傅家餐厅",
181:                 characters=["林婉晴", "李玉芬"],
182:                 lines=[
183:                     SceneLine(kind="action", text="△中近景推近规矩纸，林婉晴指尖压住纸角。"),
184:                     SceneLine(kind="dialogue", speaker="李玉芬", emotion="冷", text="这是傅家的规矩。"),
185:                     SceneLine(kind="dialogue", speaker="林婉晴", emotion="静", text="我记住了。"),
186:                 ],
187:             )
188:         ],
189:         cliffhanger="我记住了。",
190:         state_update={},
191:     )
192: 
193:     packet = build_current_episode_repair_packet(
194:         episode,
195:         "强原文轻改：当前集只能基于原文当前集做最小修复。",
196:         allow_full_rewrite=False,
197:     )
198: 
199:     assert packet.repair_mode == "creative_episode_repair"
200:     assert "最小必要改动" in packet.baseline_policy
201:     assert "整集重写" not in packet.allowed_change_scope
202: 
203: 
204: def test_quality_warnings_reject_generic_scene_heading():
205:     episode = EpisodeScript(
206:         episode=1,
207:         title="泛化场景头",
208:         hook_3s="谁敢碰她一下！",
209:         main_emotion="压迫",
210:         watch_reason="观众要看她反击。",
```
### Lines 380-465
```
380: 
381:     instruction = episode_repair_instruction(episode, "EP01 结尾钩子太软。")
382: 
383:     assert "修复级别：结尾钩子局部修复" in instruction
384:     assert "只修最后一场最后 8-12 行" in instruction
385:     assert "不要整集重写" in instruction
386:     assert "必须整集重写" not in instruction
387: 
388: 
389: def test_episode_repair_instruction_limits_action_format_to_local_patch(
390:     happy_round_outputs,
391: ):
392:     episode = happy_round_outputs[3].episodes[0].model_copy(deep=True)
393:     episode.scenes[0].lines[0].text = "△林晚站在宴会厅门口。"
394: 
395:     instruction = episode_repair_instruction(episode, "EP01 动作行格式不合格。")
396: 
397:     assert "修复级别：格式局部修复" in instruction
398:     assert "只修不合格 action 行" in instruction
399:     assert "不要整集重写" in instruction
400:     assert "必须整集重写" not in instruction
401: 
402: 
403: def test_current_episode_repair_packet_makes_existing_episode_the_baseline(
404:     happy_round_outputs,
405: ):
406:     episode = happy_round_outputs[3].episodes[0].model_copy(deep=True)
407:     episode.scenes[0].lines[0].text = "△林晚站在宴会厅门口。"
408: 
409:     packet = build_current_episode_repair_packet(
410:         episode,
411:         "EP01 动作行格式不合格。",
412:     )
413: 
414:     assert packet.episode == 1
415:     assert packet.repair_mode == "format_patch"
416:     assert "当前集旧稿是唯一文本基准" in packet.baseline_policy
417:     assert "只修不合格 action 行" in packet.allowed_change_scope
418:     assert "△林晚站在宴会厅门口。" in packet.baseline_episode_text
419:     assert any("action lines violating" in target for target in packet.editable_targets)
420:     assert "不得新增无原文依据的新剧情、新道具、新证据或新狠话" in packet.forbidden_changes
421: 
422: 
423: def test_current_episode_repair_packet_keeps_source_evidence_targets(
424:     happy_round_outputs,
425: ):
426:     episode = happy_round_outputs[3].episodes[0]
427: 
428:     packet = build_current_episode_repair_packet(
429:         episode,
430:         "原文证据未落到正片。",
431:         source_evidence_targets=["EP01 缺少原文资产：亲哥哥救场"],
432:     )
433: 
434:     assert packet.source_evidence_targets == ["EP01 缺少原文资产：亲哥哥救场"]
435:     assert packet.editable_targets[0] == "EP01 缺少原文资产：亲哥哥救场"
436:     assert packet.repair_mode == "creative_episode_repair"
437:     assert "当前集原文契约是唯一内容基准" in packet.baseline_policy
438:     assert "旧稿只作为问题定位参考" in packet.baseline_policy
439:     assert "scene_headings:" not in packet.protected_elements
440:     assert "回到当前集 source packet" in packet.allowed_change_scope
441: 
442: 
443: def test_current_episode_repair_packet_uses_source_contract_for_source_asset_gate(
444:     happy_round_outputs,
445: ):
446:     episode = happy_round_outputs[3].episodes[0]
447: 
448:     packet = build_current_episode_repair_packet(
449:         episode,
450:         "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。方法论阻断：强原文只允许轻改，必须保留 C0/C1。",
451:     )
452: 
453:     assert packet.repair_mode == "creative_episode_repair"
454:     assert "当前集原文契约是唯一内容基准" in packet.baseline_policy
455:     assert "旧稿只作为问题定位参考" in packet.baseline_policy
456:     assert "回到当前集 source packet" in packet.allowed_change_scope
457: 
458: 
459: def test_hook_dialogue_polish_instruction_targets_tail_and_dialogue_gaps():
460:     episode = EpisodeScript(
461:         episode=2,
462:         title="软结尾",
463:         hook_3s="你到底是谁？",
464:         main_emotion="悬疑",
465:         watch_reason="系统内部看点。",
```

## File: `tests/test_quality_text.py`
### Lines 1-120
```
1: from novel_drama_engine.quality_text import (
2:     dedupe_quality_items,
3:     filter_quality_text_for_episode,
4:     merge_rewrite_instructions,
5: )
6: 
7: 
8: def test_merge_rewrite_instructions_dedupes_and_filters_positive_advice():
9:     instruction = merge_rewrite_instructions(
10:         [
11:             "方法论阻断：本素材被判定为强原文，只允许轻改。具体问题：强原文轻改失败：脚本疑似命中方法论反例：把原文预谋解约改成现场赌气解约。",
12:             "The provided scripts accurately map to the source material. No blocking issues detected. Ensure that when filming, emphasize props.",
13:             "方法论阻断：本素材被判定为强原文，只允许轻改。具体问题：强原文轻改失败：脚本疑似命中方法论反例：把原文预谋解约改成现场赌气解约。",
14:             "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。",
15:             "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。",
16:         ],
17:         blocking=True,
18:     )
19: 
20:     assert instruction.count("方法论阻断") == 1
21:     assert instruction.count("source_asset_preservation") == 1
22:     assert "No blocking issues detected" not in instruction
23:     assert "Ensure that when filming" not in instruction
24: 
25: 
26: def test_dedupe_quality_items_removes_repeated_blocking_issues():
27:     items = dedupe_quality_items(
28:         [
29:             "source anchor not evidenced in script: 晚会昏暗氛围",
30:             "source anchor not evidenced in script：晚会昏暗氛围",
31:             "EP01 too short: 664 chars, expected >= 800",
32:         ]
33:     )
34: 
35:     assert items == [
36:         "source anchor not evidenced in script: 晚会昏暗氛围",
37:         "EP01 too short: 664 chars, expected >= 800",
38:     ]
39: 
40: 
41: def test_filter_quality_text_for_episode_keeps_only_target_episode_and_global_rules():
42:     text = (
43:         "方法论阻断：本素材被判定为强原文，只允许轻改；"
44:         "EP01 too short: 664 chars, expected >= 800；"
45:         "EP02 has non-shooting scene headings: 2-1 白-内-林挽清公寓；"
46:         "source_evidence: EP05 缺少原文资产：雪地烟火激吻；"
47:         "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。"
48:     )
49: 
50:     scoped = filter_quality_text_for_episode(text, 1)
51: 
52:     assert "方法论阻断" in scoped
53:     assert "EP01 too short" in scoped
54:     assert "source_asset_preservation" in scoped
55:     assert "EP02" not in scoped
56:     assert "EP05" not in scoped
57:     assert "雪地烟火激吻" not in scoped
```

## File: `tests/p0_platform.test.ts`
### Lines 250-360
```
250:   });
251: 
252:   await markProjectAfterRoundCompletion("project-p0-human-review-stop", {
253:     currentEpisode: 5,
254:     targetEpisodeCount: 25,
255:     qualityStatus: "needs_human_review",
256:     roundNumber: 1,
257:     rewriteInstruction: "EP05 原文资产缺失，需要人工复核。",
258:   });
259: 
260:   const project = await db.query.projects.findFirst({
261:     where: (projects, { eq }) => eq(projects.id, "project-p0-human-review-stop"),
262:   });
263:   assert.equal(project?.status, "failed");
264:   assert.match(project?.metaJson ?? "", /needs_human_review/);
265:   assert.match(project?.metaJson ?? "", /EP05 原文资产缺失/);
266: });
267: 
268: test("round generation job stores selected Gemini model in payload", async () => {
269:   const { db, schema } = await import("../src/db/client");
270:   const { startEngineRound } = await import("../src/lib/engine-runner");
271:   const now = new Date();
272:   await db.insert(schema.projects).values({
273:     id: "project-p0-model-select",
274:     name: "Model Select",
275:     novelText: "source",
276:     targetEpisodeCount: 5,
277:     status: "running",
278:     createdAt: now,
279:     updatedAt: now,
280:   });
281: 
282:   const started = await startEngineRound("project-p0-model-select", 1, {
283:     llmModel: "gemini_3_5_flash",
284:   });
285: 
286:   const job = await db.query.jobs.findFirst({
287:     where: (jobs, { eq }) => eq(jobs.id, started.jobId),
288:   });
289:   const payload = JSON.parse(job?.payloadJson ?? "{}") as { llmModel?: string };
290:   assert.equal(payload.llmModel, "google/gemini-3.5-flash");
291: });
292: 
293: test("engine run args include the selected model flag", async () => {
294:   const { buildEngineRunArgs } = await import("../src/lib/engine-runner");
295: 
296:   const args = buildEngineRunArgs({
297:     sourcePath: "/tmp/source.txt",
298:     engineDir: "/tmp/project",
299:     projectId: "project-model",
300:     roundNumber: 2,
301:     targetEpisodeCount: 25,
302:     episodesPerRound: 5,
303:     generationVariant: "drama_engine_first",
304:     repairBudget: "episode",
305:     llmModel: "google/gemini-3.5-flash",
306:     methodologyCardsPath: null,
307:     mock: false,
308:   });
309: 
310:   const modelIndex = args.indexOf("--model");
311:   assert.ok(modelIndex > -1);
312:   assert.equal(args[modelIndex + 1], "google/gemini-3.5-flash");
313: });
314: 
315: test("episode AI optimize prompt anchors on current draft, bible, and instruction", async () => {
316:   const { buildEpisodeOptimizationPrompt } = await import(
317:     "../src/lib/episode-ai-optimize"
318:   );
319: 
320:   const prompt = buildEpisodeOptimizationPrompt({
321:     project: {
322:       name: "名利双收",
323:       novelText: "原文：女主在颁奖礼后台被羞辱，随后提前放好的解约协议成为反击起点。",
324:     },
325:     episode: {
326:       epNum: 3,
327:       scriptTxt: "第3集 旧稿\n1-1 后台\n林挽清：我早就准备好了。",
328:     },
329:     bible: {
330:       charactersMd: "人物小传：林挽清克制、清醒，不歇斯底里。",
331:       episodePlanMd: "分集规划：第3集必须承接第2集结尾。",
332:       sixAssetsJson: "{\"核心钩子\":\"公开羞辱后的主动离开\"}",
333:       prevRoundSummaryJson: "{\"open_hooks\":[\"解约协议已埋\"]}",
334:     },
335:     round: {
336:       roundNum: 1,
337:       summaryJson: "{\"next_round_context\":{\"current_episode\":5}}",
338:     },
339:     episodes: [
340:       { epNum: 2, scriptTxt: "第2集 结尾：她把协议推到桌边。" },
341:       { epNum: 4, scriptTxt: "第4集 开头：路淮北发现她真的走了。" },
342:     ],
343:     instruction: "强化镜头和情绪递进，不要让女主突然全知全能。",
344:   });
345: 
346:   assert.match(prompt, /旧稿是唯一文本基准/);
347:   assert.match(prompt, /只优化第 3 集/);
348:   assert.match(prompt, /强化镜头和情绪递进/);
349:   assert.match(prompt, /人物小传/);
350:   assert.match(prompt, /第2集 结尾/);
351:   assert.match(prompt, /第4集 开头/);
352: });
353: 
354: test("edit impact applies user draft and optimizes impacted downstream episodes", async () => {
355:   const { db, schema } = await import("../src/db/client");
356:   const { applyEpisodeEditImpact } = await import("../src/lib/edit-impact-apply");
357:   const { parseProjectMeta } = await import("../src/lib/project-controls");
358:   const now = new Date();
359: 
360:   await db.insert(schema.projects).values({
```
### Lines 520-680
```
520:   const qualityPanel = source.slice(qualitySidePanelStart, runtimeStart);
521: 
522:   assert.doesNotMatch(qualityPanel, /round-issue-list/);
523:   assert.match(qualityPanel, /源文/);
524:   assert.match(qualityPanel, /创作/);
525:   assert.match(qualityPanel, /门禁/);
526:   assert.match(qualityPanel, /承接/);
527: });
528: 
529: test("effective quality score is capped by final source evidence and drama gates", async () => {
530:   const { effectiveQualityScore } = await import("../src/lib/engine-types");
531: 
532:   const score = effectiveQualityScore({
533:     quality_report: {
534:       status: "needs_rewrite",
535:       scores: {
536:         hook: 9,
537:         conflict: 9,
538:         cliffhanger: 9,
539:         continuity: 9,
540:         video_feasibility: 9,
541:       },
542:       blocking_issues: [],
543:       rewrite_instruction: "source similarity below 5/10",
544:     },
545:     source_evidence_report: {
546:       coverage_score: 0,
547:       items: [],
548:       missing_items: ["EP05 缺少原文资产：霍雅偷拍照片"],
549:       rewrite_instruction: "原文证据未落到正片。",
550:     },
551:     drama_quality_report: {
552:       overall_score: 5,
553:       dimensions: [
554:         {
555:           name: "source_asset_preservation",
556:           score: 0,
557:           status: "blocking",
558:           evidence: ["source similarity below 5/10: 0/100"],
559:           suggestion: "恢复原文资产。",
560:         },
561:       ],
562:       blocking_issues: ["source_asset_preservation"],
563:       advisory_warnings: [],
564:       rewrite_instruction: "恢复原文资产。",
565:     },
566:   });
567: 
568:   assert.equal(score, 0);
569: });
570: 
571: test("episode quality score is not overwritten by round-level source gate", async () => {
572:   const {
573:     effectiveQualityScore,
574:     episodeQualityScore,
575:     sourceGateScore,
576:   } = await import("../src/lib/engine-types");
577:   const result = {
578:     quality_report: {
579:       status: "needs_human_review",
580:       scores: {
581:         hook: 10,
582:         conflict: 10,
583:         cliffhanger: 9,
584:         continuity: 10,
585:         video_feasibility: 9,
586:       },
587:       blocking_issues: [],
588:       rewrite_instruction: "source gate failed",
589:     },
590:     source_evidence_report: {
591:       coverage_score: 100,
592:       items: [
593:         {
594:           episode: 1,
595:           source_anchor: "EP01 source",
596:           adaptation_reason: "matched",
597:           retained_assets: ["hook"],
598:           script_evidence: ["hook"],
599:           status: "matched",
600:         },
601:         {
602:           episode: 2,
603:           source_anchor: "EP02 source",
604:           adaptation_reason: "missing specific anchor",
605:           retained_assets: ["VIP通道黄色炽热灯光"],
606:           script_evidence: [],
607:           status: "matched",
608:         },
609:       ],
610:       missing_items: [],
611:       rewrite_instruction: "",
612:     },
613:     adaptation_quality_report: {
614:       source_fidelity: {
615:         score: 10,
616:         preserved_original_hook: true,
617:         blocking_warnings: [
618:           "source anchor not evidenced in script: VIP通道黄色炽热灯光",
619:           "forbidden addition/reveal may have leaked into script: 严禁改变林挽清解约的主动性。",
620:         ],
621:         advisory_warnings: [],
622:         checks: [
623:           {
624:             category: "source_mapping",
625:             episode: 2,
626:             status: "blocking",
627:             warning: "source anchor not evidenced in script: VIP通道黄色炽热灯光",
628:           },
629:           {
630:             category: "C4_forbidden_addition",
631:             episode: null,
632:             status: "blocking",
633:             warning: "forbidden addition/reveal may have leaked into script",
634:           },
635:         ],
636:       },
637:       continuity: { score: 90, blocking_warnings: [], advisory_warnings: [] },
638:       story_state_ledger: {
639:         current_episode: 2,
640:         entries: [],
641:         open_hooks: [],
642:         forbidden_reveals: [],
643:         character_knowledge: {},
644:         relationship_changes: [],
645:         prop_states: [],
646:         foreshadowing_ledger: [],
647:         warnings: [],
648:       },
649:       blocking_warnings: [],
650:       advisory_warnings: [],
651:       rewrite_instruction: "",
652:     },
653:     drama_quality_report: {
654:       overall_score: 5,
655:       dimensions: [
656:         {
657:           name: "source_asset_preservation",
658:           score: 1,
659:           status: "blocking",
660:           evidence: ["source similarity below 5/10: 10/100"],
661:           suggestion: "restore source",
662:         },
663:       ],
664:       blocking_issues: [],
665:       advisory_warnings: [],
666:       rewrite_instruction: "",
667:     },
668:   } as never;
669: 
670:   assert.equal(effectiveQualityScore(result), 1);
671:   assert.equal(sourceGateScore(result), 1);
672:   assert.equal(episodeQualityScore(result, 1), 9.6);
673:   assert.equal(episodeQualityScore(result, 2), 4);
674: });
675: 
676: test("engine sync computes scores per episode instead of copying one round score", () => {
677:   const source = readFileSync(
678:     path.join(repoRoot, "src/lib/engine-runner.ts"),
679:     "utf-8"
680:   );
```