"""V2 goal ranking of the full planner output, without evaluating constraints.

Scores are ordered best first, with plan IDs providing stable display order
within a tie. IDs never break a goal tie. Missing score inputs exclude a plan
with an explanation; the caller retains all original plans for inspection.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from math import isfinite
from pathlib import Path

from treatment_planner.interfaces import (
    CandidatePlan,
    CheckStatus,
    PlanningGoal,
    RecommendationResult,
    RecommendationScore,
    ResultStatus,
    RouteId,
    RouteStatus,
    RouteSummary,
    TransportMode,
)

DEADLINES = ("Ingredient arrival", "Sample arrival", "Production completion", "Injection")
LOCAL_ROUTES = (RouteId.SAMPLE, RouteId.TREATMENT)


class GoalRecommendationEngine:
    """Implement RecommendationEngine using the agreed V2-1 scoring rules.

    Route summaries describe the same candidate journeys as the plans. Only
    explicit, evidence-backed At risk local routes count as warnings. An omitted
    summary adds no warning; it does not establish route safety or coverage.
    Supplied Unknown/Blocked summaries prevent recommendation of that candidate.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        path = config_path or Path(__file__).resolve().parents[2] / "config/recommendations.json"
        values = json.loads(path.read_text(encoding="utf-8"))
        self.early_weight = self._weight(values["injection_early_weight"])
        self.late_weight = self._weight(values["injection_late_weight"])

    @staticmethod
    def _weight(value: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Injection weights must be finite positive numbers.")
        if not isfinite(value) or value <= 0:
            raise ValueError("Injection weights must be finite positive numbers.")
        return value

    def recommend(
        self,
        plans: tuple[CandidatePlan, ...],
        goal: PlanningGoal,
        target_injection: datetime | None,
        route_summaries: tuple[RouteSummary, ...],
    ) -> RecommendationResult:
        """Return ordered scores and every best-scoring confirmed plan ID."""
        goal = PlanningGoal(goal)
        if len({plan.plan_id for plan in plans}) != len(plans):
            raise ValueError("Candidate plan IDs must be unique.")
        if goal == PlanningGoal.INJECTION_TIMING:
            if target_injection is None:
                return RecommendationResult(
                    goal, (), (), "Enter a target injection time to rank plans."
                )
            if target_injection.tzinfo is None or target_injection.utcoffset() is None:
                raise ValueError("Use a timezone-aware target injection time.")

        scores, exclusions = [], []
        for plan in plans:
            summaries = tuple(s for s in route_summaries if s.plan_id == plan.plan_id)
            issue = self._eligibility_issue(plan, summaries)
            if issue:
                exclusions.append(f"{plan.plan_id}: {issue}")
                continue
            score = self._score(plan, goal, target_injection, summaries)
            if score is None:
                exclusions.append(f"{plan.plan_id}: missing required {goal.value} score inputs")
            else:
                scores.append(score)
        scores.sort(key=lambda score: (self._key(score, goal), score.plan_id))
        ordered = tuple(scores)
        if not ordered:
            reason = self._explanation(plans, goal, ordered, (), target_injection)
            if exclusions:
                reason += "\nExcluded from ranking:\n- " + "\n- ".join(sorted(exclusions))
            return RecommendationResult(goal, (), (), reason)
        primary_winners = tuple(
            score.plan_id
            for score in ordered
            if self._key(score, goal) == self._key(ordered[0], goal)
        )
        primary_plans = {plan.plan_id: plan for plan in plans if plan.plan_id in primary_winners}
        best_mode_preference = max(self._mode_preference(plan) for plan in primary_plans.values())
        winners = tuple(
            plan_id
            for plan_id in primary_winners
            if self._mode_preference(primary_plans[plan_id]) == best_mode_preference
        )
        reason = self._explanation(
            plans,
            goal,
            ordered,
            winners,
            target_injection,
            mode_tiebreak=len(winners) < len(primary_winners),
        )
        if exclusions:
            reason += "\nExcluded from ranking:\n- " + "\n- ".join(sorted(exclusions))
        return RecommendationResult(goal, winners, ordered, reason)

    @staticmethod
    def _eligibility_issue(plan: CandidatePlan, summaries: tuple[RouteSummary, ...]) -> str | None:
        if plan.status != ResultStatus.CONFIRMED:
            details = "; ".join(
                f"{check.constraint}: {check.reason}"
                for check in plan.checks
                if check.status != CheckStatus.PASS
            )
            return f"{plan.status.value}" + (f" ({details})" if details else "")
        if not plan.checks or any(check.status != CheckStatus.PASS for check in plan.checks):
            return "required checks have not all passed"
        if any(s.status in (RouteStatus.UNKNOWN, RouteStatus.BLOCKED) for s in summaries):
            return "route summary is blocked or unknown"
        if any(
            s.status == RouteStatus.AT_RISK and (not s.evidence or not s.reason.strip())
            for s in summaries
        ):
            return "route warning lacks evidence or an explanation"
        return None

    def _score(self, plan, goal, target, summaries) -> RecommendationScore | None:
        checks = {check.constraint: check for check in plan.checks}
        if goal == PlanningGoal.INJECTION_TIMING:
            injection = checks.get("Injection")
            if injection is None or injection.actual_time is None:
                return None
            minutes = (injection.actual_time - target).total_seconds() / 60
            penalty = abs(minutes) * (self.early_weight if minutes < 0 else self.late_weight)
            return RecommendationScore(plan.plan_id, injection_penalty_minutes=penalty)
        if goal == PlanningGoal.INGREDIENT_DELIVERY:
            arrival = checks.get("Ingredient arrival")
            if arrival is None or arrival.actual_time is None:
                return None
            return RecommendationScore(plan.plan_id, ingredient_arrival=arrival.actual_time)
        margins = [checks[name].margin for name in DEADLINES if name in checks]
        if len(margins) != len(DEADLINES) or any(m is None or m < timedelta() for m in margins):
            return None
        warned_routes = {
            s.route
            for s in summaries
            if s.route in LOCAL_ROUTES and s.status == RouteStatus.AT_RISK
        }
        return RecommendationScore(
            plan.plan_id, limiting_margin=min(margins), at_risk_routes=len(warned_routes)
        )

    @staticmethod
    def _key(score, goal):
        if goal == PlanningGoal.INJECTION_TIMING:
            return (score.injection_penalty_minutes,)
        if goal == PlanningGoal.INGREDIENT_DELIVERY:
            return (score.ingredient_arrival,)
        return (-score.limiting_margin, score.at_risk_routes)

    @staticmethod
    def _mode_preference(plan: CandidatePlan) -> tuple[int, int]:
        """Prefer ship before comparing the number of bicycle legs to car legs."""
        return (
            int(plan.ingredient_mode == TransportMode.SHIP),
            int(plan.outbound_mode == TransportMode.BICYCLE)
            + int(plan.return_mode == TransportMode.BICYCLE),
        )

    def _explanation(self, plans, goal, scores, winners, target, *, mode_tiebreak=False) -> str:
        if not scores:
            return (
                f"No recommendation for {goal.value}: "
                "no confirmed alternative has usable score inputs."
            )
        best = next(score for score in scores if score.plan_id == winners[0])
        plan = next(p for p in plans if p.plan_id == best.plan_id)
        checks = {check.constraint: check for check in plan.checks}
        example = "example tied winner: " if len(winners) > 1 else ""
        if goal == PlanningGoal.INJECTION_TIMING:
            minutes = (checks["Injection"].actual_time - target).total_seconds() / 60
            direction = "early" if minutes < 0 else "late" if minutes > 0 else "on target"
            reason = (
                "Injection timing: smallest weighted deviation is "
                f"{best.injection_penalty_minutes:g} points "
                f"({example}{abs(minutes):g} minutes {direction}; "
                f"early weight {self.early_weight:g}, late weight {self.late_weight:g})."
            )
        elif goal == PlanningGoal.INGREDIENT_DELIVERY:
            reason = (
                f"Ingredient delivery timing: earliest confirmed arrival at production is "
                f"{best.ingredient_arrival.isoformat()} "
                f"({example}{plan.ingredient_mode.value})."
            )
        else:
            limiting = ", ".join(
                name for name in DEADLINES if checks[name].margin == best.limiting_margin
            )
            reason = (
                f"Lower disruption risk: largest minimum deadline margin is "
                f"{best.limiting_margin.total_seconds() / 60:g} minutes "
                f"({example}limited by {limiting})."
            )
            equal_margin = [s for s in scores if s.limiting_margin == best.limiting_margin]
            if any(s.at_risk_routes != best.at_risk_routes for s in equal_margin):
                reason += (
                    " Tie-break: fewer evidence-backed At risk local routes "
                    f"({best.at_risk_routes})."
                )
        if mode_tiebreak:
            reason += (
                " Route-mode tie-break applied: prefer Rhine ship to truck first, "
                "then prefer more bicycle legs over car legs."
            )
        if len(winners) > 1:
            reason += f" {len(winners)} equal winners remain; no automatic preselection."
        return reason
