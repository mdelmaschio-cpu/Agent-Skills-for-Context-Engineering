"""BDI Agent: Belief-Desire-Intention cognitive architecture simulation.

Demonstrates key BDI patterns from the bdi-mental-states skill:
  - Mental state modeling (Belief, Desire, Intention)
  - Cognitive chain: world state → belief → desire → intention → plan
  - T2B2T pipeline (Triples-to-Beliefs-to-Triples)
  - Temporal validity intervals
  - Compositional beliefs with part relations
  - Justifications for explainability

All reasoning is pure Python — no LLM calls. Replace ``deliberate`` with
an LLM call when deploying to a real agent system.

Typical usage::

    agent = BDIAgent("shopping_agent")
    ws = WorldState("store_open", "Store is open until 10pm")
    agent.perceive(ws)
    agent.deliberate()
    agent.act()

Run directly (``python bdi_agent.py``) for an interactive demo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

__all__ = [
    "TimeInterval",
    "Justification",
    "WorldState",
    "Belief",
    "Desire",
    "Intention",
    "Task",
    "Plan",
    "BeliefProcess",
    "BDIAgent",
    "T2B2TPipeline",
]


# ---------------------------------------------------------------------------
# Temporal
# ---------------------------------------------------------------------------


@dataclass
class TimeInterval:
    """Validity window for a mental state.

    Use when: bounding beliefs so stale ones can be garbage-collected.
    Every mental state should carry one of these.
    """

    start: datetime
    end: datetime

    def is_active(self, at: Optional[datetime] = None) -> bool:
        """Return True if the interval is active at *at* (defaults to now)."""
        now = at or datetime.now()
        return self.start <= now <= self.end

    def __str__(self) -> str:
        fmt = "%H:%M"
        return f"[{self.start.strftime(fmt)}, {self.end.strftime(fmt)}]"


# ---------------------------------------------------------------------------
# Justification
# ---------------------------------------------------------------------------


@dataclass
class Justification:
    """Evidence or rule that produced a mental state.

    Use when: every mental entity needs an audit trail. Unjustified states
    make agent reasoning opaque.
    """

    evidence: str
    source: str = "perception"

    def __str__(self) -> str:
        return f"({self.source}) {self.evidence}"


# ---------------------------------------------------------------------------
# World State
# ---------------------------------------------------------------------------


@dataclass
class WorldState:
    """Objective world configuration, independent of agent perspective.

    World states are the referential substrate for beliefs. Agents perceive
    world states; they do not hold world states themselves.
    """

    id: str
    description: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    observed_at: datetime = field(default_factory=datetime.now)

    def to_triples(self) -> List[tuple]:
        """Serialize to (subject, predicate, object) triples.

        Use when: implementing the Beliefs-to-Triples phase of T2B2T.
        """
        triples = [
            (self.id, "rdf:type", "bdi:WorldState"),
            (self.id, "rdfs:comment", self.description),
            (self.id, "bdi:atTime", self.observed_at.isoformat()),
        ]
        for k, v in self.attributes.items():
            triples.append((self.id, k, str(v)))
        return triples


# ---------------------------------------------------------------------------
# Mental States
# ---------------------------------------------------------------------------


@dataclass
class Belief:
    """What the agent holds true about a world state.

    Always ground beliefs in a WorldState reference — do not put factual
    claims directly in the belief without a referent.
    """

    id: str
    content: str
    world_state: WorldState
    justification: Optional[Justification] = None
    validity: Optional[TimeInterval] = None
    parts: List["Belief"] = field(default_factory=list)

    def is_valid(self, at: Optional[datetime] = None) -> bool:
        """Return True if the belief is temporally active."""
        if self.validity is None:
            return True
        return self.validity.is_active(at)

    def __str__(self) -> str:
        return f"Belief({self.id}): {self.content}"


@dataclass
class Desire:
    """What the agent wishes to bring about.

    Link every desire to the beliefs that motivate it. This preserves the
    motivational chain for explainability.
    """

    id: str
    goal: str
    motivated_by: List[Belief] = field(default_factory=list)
    priority: int = 5  # 1 (low) .. 10 (high)
    justification: Optional[Justification] = None
    validity: Optional[TimeInterval] = None

    def is_achievable(self) -> bool:
        """Return True if all motivating beliefs are currently valid."""
        return all(b.is_valid() for b in self.motivated_by)

    def __str__(self) -> str:
        return f"Desire({self.id}): {self.goal} [priority={self.priority}]"


@dataclass
class Task:
    """Atomic step in a plan.

    Use when: decomposing intentions into executable primitives. Tasks are
    ordered with ``precedes`` to make execution order explicit.
    """

    id: str
    description: str
    precedes: Optional["Task"] = None

    def sequence(self) -> List["Task"]:
        """Return the full ordered task sequence from this task onward."""
        result = [self]
        current = self
        while current.precedes is not None:
            current = current.precedes
            result.append(current)
        return result

    def __str__(self) -> str:
        return f"Task({self.id}): {self.description}"


@dataclass
class Plan:
    """Ordered sequence of tasks addressing a goal.

    Plans are reusable — multiple intentions can share the same plan.
    """

    id: str
    description: str
    first_task: Optional[Task] = None

    def tasks(self) -> List[Task]:
        """Return all tasks in execution order."""
        if self.first_task is None:
            return []
        return self.first_task.sequence()

    def __str__(self) -> str:
        task_list = " → ".join(t.id for t in self.tasks())
        return f"Plan({self.id}): {self.description} [{task_list}]"


@dataclass
class Intention:
    """What the agent commits to achieving.

    An intention must fulfil a desire and specify a plan. This two-step
    indirection (desire → intention → plan) keeps planning separate from
    motivation.
    """

    id: str
    commitment: str
    fulfils: Optional[Desire] = None
    plan: Optional[Plan] = None
    supported_by: List[Belief] = field(default_factory=list)
    justification: Optional[Justification] = None

    def execute(self) -> List[str]:
        """Return the list of action strings for this intention's plan.

        In production, replace with real tool calls or actuator dispatches.
        """
        if self.plan is None:
            return [f"[no plan] {self.commitment}"]
        return [str(t) for t in self.plan.tasks()]

    def __str__(self) -> str:
        plan_id = self.plan.id if self.plan else "none"
        return f"Intention({self.id}): {self.commitment} via plan={plan_id}"


# ---------------------------------------------------------------------------
# Belief Formation Process
# ---------------------------------------------------------------------------


@dataclass
class BeliefProcess:
    """Causal record of how a belief was formed from a world state.

    Use when: tracking provenance from perception through to action.
    One BeliefProcess per world state → belief transition.
    """

    id: str
    triggered_by: WorldState
    generates: Optional[Belief] = None

    def run(self) -> Belief:
        """Execute the process: produce a Belief from the triggering WorldState."""
        if self.generates is not None:
            return self.generates
        belief = Belief(
            id=f"belief_{self.triggered_by.id}",
            content=self.triggered_by.description,
            world_state=self.triggered_by,
            justification=Justification(
                evidence=f"Perceived: {self.triggered_by.description}",
                source="perception",
            ),
        )
        self.generates = belief
        return belief


# ---------------------------------------------------------------------------
# BDI Agent
# ---------------------------------------------------------------------------


class BDIAgent:
    """Minimal BDI agent demonstrating the belief-desire-intention cycle.

    Use when: implementing deliberative reasoning with traceable chains
    from perception through to action.

    The deliberation loop:
    1. ``perceive``   — ingest world states, form beliefs
    2. ``deliberate`` — generate desires from beliefs, select intentions
    3. ``act``        — execute the intention's plan tasks

    In production, the heuristics inside ``deliberate`` should be replaced
    with an LLM call that reasons over the current belief set.
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id: str = agent_id
        self.beliefs: List[Belief] = []
        self.desires: List[Desire] = []
        self.intentions: List[Intention] = []
        self._world_states: List[WorldState] = []
        self._action_log: List[str] = []

    # --- Perception phase ---

    def perceive(self, world_state: WorldState) -> Belief:
        """Ingest a world state and form a grounded belief.

        Use when: new observations arrive from sensors, tools, or other agents.
        """
        process = BeliefProcess(
            id=f"bp_{world_state.id}",
            triggered_by=world_state,
        )
        belief = process.run()
        self._world_states.append(world_state)
        self.beliefs.append(belief)
        return belief

    # --- Deliberation phase ---

    def deliberate(self) -> None:
        """Generate desires from current beliefs and select intentions.

        Heuristic implementation — replace with LLM reasoning in production.
        Processes only currently-valid beliefs.
        """
        self.desires.clear()
        self.intentions.clear()

        active = [b for b in self.beliefs if b.is_valid()]
        if not active:
            return

        for belief in active:
            desire = self._generate_desire(belief)
            if desire:
                self.desires.append(desire)

        self.desires.sort(key=lambda d: d.priority, reverse=True)

        for desire in self.desires:
            if desire.is_achievable():
                intention = self._commit_to_intention(desire)
                self.intentions.append(intention)
                break  # Commit to the highest-priority achievable desire

    def _generate_desire(self, belief: Belief) -> Optional[Desire]:
        """Heuristic: derive a desire from a belief.

        In production, call an LLM with the belief content and current
        goal ontology to derive a ranked desire.
        """
        desire = Desire(
            id=f"desire_{belief.id}",
            goal=f"Act on: {belief.content}",
            motivated_by=[belief],
            priority=5,
            justification=Justification(
                evidence=f"Motivated by belief: {belief.content}",
                source="deliberation",
            ),
        )
        return desire

    def _commit_to_intention(self, desire: Desire) -> Intention:
        """Commit to an intention that fulfils the given desire."""
        t1 = Task(id="t1", description=f"Prepare for: {desire.goal}")
        t2 = Task(id="t2", description=f"Execute: {desire.goal}")
        t3 = Task(id="t3", description=f"Verify: {desire.goal}")
        t1.precedes = t2
        t2.precedes = t3

        plan = Plan(
            id=f"plan_{desire.id}",
            description=f"Plan for {desire.goal}",
            first_task=t1,
        )

        intention = Intention(
            id=f"intention_{desire.id}",
            commitment=desire.goal,
            fulfils=desire,
            plan=plan,
            supported_by=desire.motivated_by,
            justification=Justification(
                evidence=f"Committed to fulfil: {desire.goal}",
                source="intention_formation",
            ),
        )
        return intention

    # --- Action phase ---

    def act(self) -> List[str]:
        """Execute the current intentions and return action strings.

        Use when: the deliberation cycle has selected an intention and the
        agent is ready to produce external effects.
        """
        actions: List[str] = []
        for intention in self.intentions:
            for action in intention.execute():
                self._action_log.append(action)
                actions.append(action)
        return actions

    # --- T2B2T output ---

    def beliefs_to_triples(self) -> List[tuple]:
        """Project current beliefs back to RDF triples (T2B2T Phase 2).

        Use when: downstream systems need agent outputs as linked data.
        """
        triples: List[tuple] = []
        triples.append((self.agent_id, "rdf:type", "bdi:Agent"))

        for ws in self._world_states:
            triples.append((self.agent_id, "bdi:perceives", ws.id))
            triples.extend(ws.to_triples())

        for belief in self.beliefs:
            triples.append((self.agent_id, "bdi:hasMentalState", belief.id))
            triples.append((belief.id, "rdf:type", "bdi:Belief"))
            triples.append((belief.id, "rdfs:comment", belief.content))
            triples.append((belief.id, "bdi:refersTo", belief.world_state.id))
            if belief.justification:
                j_id = f"just_{belief.id}"
                triples.append((belief.id, "bdi:isJustifiedBy", j_id))
                triples.append((j_id, "rdfs:comment", str(belief.justification)))

        for intention in self.intentions:
            if intention.fulfils:
                triples.append((intention.id, "rdf:type", "bdi:Intention"))
                triples.append((intention.id, "bdi:fulfils", intention.fulfils.id))
            if intention.plan:
                triples.append((intention.id, "bdi:specifies", intention.plan.id))

        return triples

    def state_summary(self) -> Dict[str, Any]:
        """Return a snapshot of current mental states."""
        return {
            "agent": self.agent_id,
            "beliefs": [str(b) for b in self.beliefs if b.is_valid()],
            "desires": [str(d) for d in self.desires],
            "intentions": [str(i) for i in self.intentions],
            "action_log": list(self._action_log),
        }


# ---------------------------------------------------------------------------
# T2B2T Pipeline
# ---------------------------------------------------------------------------


class T2B2TPipeline:
    """Bidirectional Triples-to-Beliefs-to-Triples pipeline.

    Use when: an agent must consume external RDF context and produce new
    RDF assertions, preserving provenance throughout.

    Phase 1 (Triples → Beliefs): parse incoming triples into WorldState
    objects, then feed them to the agent's perception phase.

    Phase 2 (Beliefs → Triples): after deliberation, project mental states
    back to RDF via ``agent.beliefs_to_triples()``.
    """

    def __init__(self, agent: BDIAgent) -> None:
        self.agent: BDIAgent = agent
        self.input_triples: List[tuple] = []
        self.output_triples: List[tuple] = []

    def ingest(self, triples: List[tuple]) -> None:
        """Phase 1: translate incoming triples into agent beliefs.

        Triples with predicate ``rdfs:comment`` are treated as world state
        descriptions and trigger belief formation.
        """
        self.input_triples.extend(triples)
        subjects: Dict[str, Dict[str, str]] = {}

        for subj, pred, obj in triples:
            subjects.setdefault(subj, {})
            subjects[subj][pred] = obj

        for subj, props in subjects.items():
            if props.get("rdf:type") == "bdi:WorldState":
                ws = WorldState(
                    id=subj,
                    description=props.get("rdfs:comment", subj),
                    attributes={k: v for k, v in props.items()
                                if k not in ("rdf:type", "rdfs:comment", "bdi:atTime")},
                )
                self.agent.perceive(ws)

    def project(self) -> List[tuple]:
        """Phase 2: project agent mental states back to RDF triples."""
        self.output_triples = self.agent.beliefs_to_triples()
        return self.output_triples


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("=== BDI Agent Demo ===\n")

    # ---- Scenario: agent receives a push notification about a payment ----

    # Phase 1: Triples → Beliefs
    print("-- Phase 1: T2B2T ingestion --")

    now = datetime.now()
    agent = BDIAgent("finance_agent")
    pipeline = T2B2TPipeline(agent)

    incoming_triples = [
        ("ws_payment", "rdf:type", "bdi:WorldState"),
        ("ws_payment", "rdfs:comment", "Push notification: Payment request $250"),
        ("ws_payment", "bdi:atTime", now.isoformat()),
        ("ws_payment", "amount", "250"),
        ("ws_payment", "currency", "USD"),
        ("ws_store", "rdf:type", "bdi:WorldState"),
        ("ws_store", "rdfs:comment", "Store is open until 10pm"),
        ("ws_store", "bdi:atTime", now.isoformat()),
    ]

    pipeline.ingest(incoming_triples)
    print(f"Ingested {len(incoming_triples)} triples → formed {len(agent.beliefs)} beliefs")
    for belief in agent.beliefs:
        print(f"  {belief}")

    # Deliberation
    print("\n-- Deliberation cycle --")
    agent.deliberate()
    summary = agent.state_summary()

    print(f"Desires formed  : {len(summary['desires'])}")
    for d in summary["desires"]:
        print(f"  {d}")

    print(f"Intentions set  : {len(summary['intentions'])}")
    for i in summary["intentions"]:
        print(f"  {i}")

    # Action execution
    print("\n-- Action execution --")
    actions = agent.act()
    for action in actions:
        print(f"  > {action}")

    # Phase 2: Beliefs → Triples
    print("\n-- Phase 2: project mental states back to triples --")
    output_triples = pipeline.project()
    print(f"Exported {len(output_triples)} triples")
    for s, p, o in output_triples[:8]:
        print(f"  ({s}, {p}, {o})")
    if len(output_triples) > 8:
        print(f"  ... and {len(output_triples) - 8} more")

    # ---- Compositional belief demo ----
    print("\n-- Compositional belief (meeting scenario) --")

    time_belief = Belief(
        id="belief_meeting_time",
        content="Meeting at 10am",
        world_state=WorldState("ws_time", "Time: 10am"),
        justification=Justification("Calendar entry", "calendar_api"),
        validity=TimeInterval(
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=2),
        ),
    )
    location_belief = Belief(
        id="belief_meeting_location",
        content="Meeting in Room 5",
        world_state=WorldState("ws_location", "Room: 5"),
        justification=Justification("Booking system", "room_api"),
        validity=TimeInterval(
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=2),
        ),
    )
    composite = Belief(
        id="belief_meeting",
        content="Meeting at 10am in Room 5",
        world_state=WorldState("ws_meeting", "Meeting scheduled"),
        parts=[time_belief, location_belief],
    )
    print(f"Composite: {composite}")
    print(f"  Parts   : {[str(p) for p in composite.parts]}")
    print(f"  Time valid : {time_belief.is_valid()}")
    print(f"  Loc valid  : {location_belief.is_valid()}")

    # ---- Cognitive chain summary ----
    print("\n-- Cognitive chain summary --")
    if agent.intentions:
        intention = agent.intentions[0]
        desire = intention.fulfils
        beliefs = intention.supported_by
        print(f"Belief  → {beliefs[0] if beliefs else 'none'}")
        print(f"Desire  → {desire}")
        print(f"Intention → {intention}")
        if intention.plan:
            print(f"Plan    → {intention.plan}")
            for task in intention.plan.tasks():
                print(f"  Task  → {task}")
