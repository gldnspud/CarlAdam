import pytest
from pyrsistent import pset

from carladam.petrinet import errors
from carladam.petrinet.arc import Annotate, CompletedArcPT, CompletedArcTP, TransformEach, arc
from carladam.petrinet.color import Abstract, Color
from carladam.petrinet.marking import marking_colorset
from carladam.petrinet.petrinet import PetriNet
from carladam.petrinet.place import Place
from carladam.petrinet.token import Token
from carladam.petrinet.transition import Transition, passthrough


@pytest.mark.parametrize("ltr", [True, False])
def test_from_place_to_transition(ltr: bool):
    net = PetriNet.new(
        p0 := Place(),
        t0 := Transition(),
        a0 := p0 >> t0 if ltr else t0 << p0,
    )
    assert a0.src == p0
    assert a0.dest == t0
    assert not net.node_inputs.get(p0)
    assert net.node_outputs[p0] == {a0}
    assert net.node_inputs[t0] == {a0}
    assert not net.node_outputs.get(t0)


@pytest.mark.parametrize("ltr", [True, False])
def test_from_transition_to_place(ltr: bool):
    net = PetriNet.new(
        p0 := Place(),
        t0 := Transition(),
        a0 := t0 >> p0 if ltr else p0 << t0,
    )
    assert a0.src == t0
    assert a0.dest == p0
    assert not net.node_inputs.get(t0)
    assert net.node_outputs[t0] == {a0}
    assert net.node_inputs[p0] == {a0}
    assert not net.node_outputs.get(p0)


def test_from_place_to_place_not_valid():
    with pytest.raises(TypeError):
        Place() >> Place()  # type: ignore
    with pytest.raises(TypeError):
        Place() << Place()  # type: ignore


def test_from_transition_to_transition_not_valid():
    with pytest.raises(TypeError):
        Transition() >> Transition()  # type: ignore
    with pytest.raises(TypeError):
        Transition() << Transition()  # type: ignore


def test_is_hashable():
    p0, t0, p1 = Place(), Transition(), Place()
    a0 = p0 >> t0
    a1 = t0 >> p1
    a2 = t0 >> p1
    s = {a0, a1}
    s.update({a2})
    assert len(s) == 2


def test_weight():
    net = PetriNet.new(
        p0a := Place(),
        p0b := Place(),
        t0 := Transition(fn=Abstract.produce(3)),
        p1 := Place(),
        p0a >> t0,
        p0b >> {Abstract: 2} >> t0,
        t0 >> {Abstract: 3} >> p1,
    )

    m0 = {
        p0a: {Token()},
        p0b: {Token()},
    }
    assert not net.transition_is_enabled(m0, t0)
    m0 = {
        p0a: {Token()},
        p0b: {Token(), Token()},
    }
    assert net.transition_is_enabled(m0, t0)
    m1 = net.marking_after_transition(m0, t0)
    assert marking_colorset(m1) == {
        p1: {Abstract: 3},
    }


def test_weight_shorthand_using_color():
    p = Place()
    t = Transition()
    c = Color("C")

    for arc in (
        p >> c >> t,
        p << c << t,
        t >> c >> p,
        t << c << p,
    ):
        assert arc.weight == {c: 1}


def test_weight_shorthand_using_sets():
    p = Place()
    t = Transition()
    c0 = Color("0")
    c1 = Color("1")
    expected_weight = {c0: 1, c1: 1}
    a0 = p >> {c0, c1} >> t
    a1 = p >> frozenset({c0, c1}) >> t
    a2 = p >> pset({c0, c1}) >> t
    a3 = t >> {c0, c1} >> p
    a4 = t >> frozenset({c0, c1}) >> p
    a5 = t >> pset({c0, c1}) >> p
    assert all(expected_weight == a.weight for a in [a0, a1, a2, a3, a4, a5])


def test_annotate():
    p = Place()
    t = Transition()
    a0 = p >> t >> Annotate("A0")
    a1 = t >> Abstract >> Annotate("A1") >> p
    assert a0.annotation == "A0"
    assert "A0" in repr(a0)
    assert a1.annotation == "A1"


def test_incomplete():
    net = PetriNet.new(p := Place())
    a = p >> Abstract >> Annotate("A")
    with pytest.raises(errors.PetriNetArcIncomplete):
        net.update(a)


def test_transform_each():
    def x_plus_1(token):
        return token.replace(x=token.data.get("x", 0) + 1)

    def x_minus_2(token):
        return token.replace(x=token.data.get("x", 0) - 2)

    net = PetriNet.new(
        p := Place(),
        t := Transition(fn=passthrough()),
        a0 := (p >> t >> TransformEach(x_plus_1)),  # [TODO] p >> TransformEach(x_plus_1) >> t
        t >> p >> TransformEach(x_minus_2),
    )
    assert a0.transform is not None

    m0 = {p: {Token()}}
    m1 = net.marking_after_transition(m0, t)
    assert marking_colorset(m1) == {p: {Abstract: 1}}
    token = next(iter(m1[p]))
    assert token.data["x"] == -1


def test_sorts_by_src_name_then_dest_name():
    p = Place("P")
    t = Transition("T")
    a0 = t >> p
    a1 = p >> t
    assert list(sorted([a0, a1])) == [a1, a0]


def test_lshift_equivalence():
    p = Place()
    t = Transition()
    c0 = Color("0")
    c1 = Color("1")

    assert p >> {c0, c1} >> t == t << {c0, c1} << p
    assert p >> frozenset({c0, c1}) >> t == t << frozenset({c0, c1}) << p
    assert p >> pset({c0, c1}) >> t == t << pset({c0, c1}) << p

    assert t >> {c0, c1} >> p == p << {c0, c1} << t
    assert t >> frozenset({c0, c1}) >> p == p << frozenset({c0, c1}) << t
    assert t >> pset({c0, c1}) >> p == p << pset({c0, c1}) << t

    assert p >> t >> Annotate("A0") == t << p << Annotate("A0")
    assert t >> Abstract >> Annotate("A1") >> p == p << Abstract << Annotate("A1") << t


def test_cannot_overwrite_already_set_endpoints():
    p = Place()
    t = Transition()

    arc = p << {Abstract: 1}
    with pytest.raises(errors.PetriNetArcIncomplete):
        arc >> p

    arc = t << {Abstract: 1}
    with pytest.raises(errors.PetriNetArcIncomplete):
        arc >> t

    arc = p >> {Abstract: 1}
    with pytest.raises(errors.PetriNetArcIncomplete):
        arc << p

    arc = t >> {Abstract: 1}
    with pytest.raises(errors.PetriNetArcIncomplete):
        arc << t


def test_arc_pt_guard():
    def inhibitor(arc, tokens):
        return not tokens

    net = PetriNet.new(
        p_input := Place(),
        p_yes := Place(),
        p_no := Place(),
        t_yes := Transition(),
        t_no := Transition(),
        p_input >> t_yes,  # default guard is to require an abstract token to be present
        (p_input >> t_no)(guard=inhibitor),
        t_yes >> p_yes,
        t_no >> p_no,
    )

    yes_is_enabled = {p_input: {Token()}}
    no_is_enabled = {}

    assert net.transition_is_enabled(yes_is_enabled, t_yes)
    assert not net.transition_is_enabled(yes_is_enabled, t_no)

    assert not net.transition_is_enabled(no_is_enabled, t_yes)
    assert net.transition_is_enabled(no_is_enabled, t_no)


def test_arc_pt_guard_raises_exception():
    def guard_raises_exception(arc, tokens):
        raise ValueError("This guard always raises an exception")

    net = PetriNet.new(
        p := Place(),
        t := Transition(),
        (p >> t)(guard=guard_raises_exception),
    )

    with pytest.raises(errors.ArcGuardRaisesException) as e:
        net.transition_is_enabled({p: {Token()}}, t)
    assert isinstance(e.value.__cause__, ValueError)


@pytest.mark.parametrize(
    "src, dest, expected_type",
    [
        (Place(), Transition(), CompletedArcPT),
        (Transition(), Place(), CompletedArcTP),
    ],
)
def test_arc_factory(src, dest, expected_type):
    a = arc(src, dest)
    assert a.src == src
    assert a.dest == dest
    assert isinstance(a, expected_type)


@pytest.mark.parametrize(
    "src, dest",
    [
        (Place(), Place()),
        (Transition(), Transition()),
    ],
)
def test_arc_factory_raises_type_error_for_incompatible_nodes(src, dest):
    with pytest.raises(TypeError):
        arc(src, dest)
