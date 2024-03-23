from carladam import Abstract, Annotate, Color, PetriNet, Place, TransformEach, Transition

Coin = Color("🪙")
Packet = Color("📦")
Counter = Color("🧮")


def x_minus_1(token):
    return token.replace(x=token.data["x"] - 1)


def counter_x_gt_0(inputs):
    counters = (token for token in inputs if token.color == Counter)
    return all(counter.data["x"] > 0 for counter in counters)


class UnderstandingPetriNetsFigure_1_12(PetriNet):  # noqa
    """
    Understanding Petri Nets: Figure 1.12

    "At most one coin in the coin slot and at most one signal pending."
    """

    class Structure:
        class P:
            cash_box = Place()
            coin_slot = Place()
            compartment = Place()
            counter = Place()
            insertion_possible = Place()
            no_signal = Place()
            signal = Place()
            storage = Place()

        class T:
            a = Transition(
                guard=counter_x_gt_0,
                annotation="x > 0",
                fn=[Coin.produce(), Abstract.produce(), Counter.passthrough()],
            )
            b = Transition(fn=[Abstract.produce(), Packet.produce()])
            insert_coin = Transition(fn=Coin.produce())
            return_coin = Transition()
            take_packet = Transition()

        arcs = {
            P.coin_slot >> Coin >> T.a,
            P.coin_slot >> Coin >> T.return_coin,
            P.compartment >> Packet >> T.take_packet,
            P.counter >> Counter >> Annotate("x") >> T.a,
            P.insertion_possible >> T.insert_coin,
            P.no_signal >> T.a,
            P.signal >> T.b,
            P.storage >> Packet >> T.b,
            T.a >> Coin >> P.cash_box,
            T.a >> Counter >> Annotate("x-1") >> TransformEach(x_minus_1) >> P.counter,
            T.a >> P.insertion_possible,
            T.a >> P.signal,
            T.b >> Packet >> P.compartment,
            T.b >> P.no_signal,
            T.insert_coin >> Coin >> P.coin_slot,
            T.return_coin >> P.insertion_possible,
        }

        example_markings = {
            "Figure 1.12: At most one coin in the coin slot and it most one signal pending": {},
            "Initialized vending machine": {
                P.counter: {Counter(x=5)},
                P.insertion_possible: {Abstract()},
                P.no_signal: {Abstract()},
                P.storage: Packet() * 5,
            },
        }

        clusters = {
            "": {
                T.insert_coin,
                P.coin_slot,
                T.a,
                P.signal,
                T.b,
                P.compartment,
                T.take_packet,
            },
            "Coin return": {
                T.return_coin,
                P.insertion_possible,
            },
        }
