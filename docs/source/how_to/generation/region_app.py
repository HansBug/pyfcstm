from machine import ControllerMachine


class Device(ControllerMachine):
    def __init__(self, sensors, **kwargs):
        self.sensors = sensors
        super().__init__(**kwargs)

    def read_fault(self) -> int:
        return self.sensors["fault"]

    def read_requested(self) -> int:
        return self.sensors["requested"]


def show(label, machine):
    print(f"{label}: {machine.configuration}")
    print(f"  leaves {['.'.join(leaf) for leaf in machine.leaves]}")
    print(f"  motor={machine.vars['motor']} permit={machine.vars['permit']}")


sensors = {"fault": 0, "requested": 1}
machine = Device(sensors)
machine.cycle()
machine.cycle(["/Start"])
machine.cycle()
show("after start", machine)
print("is_active Running:", machine.is_active("Controller.Running"))
print("region_status Safety:", machine.region_status("Controller.Running.Safety"))

sensors["fault"] = 1
machine.cycle()
show("fault raised", machine)

restored = Device(
    sensors,
    initial_state="Controller.Running{Safety: Watching, Motion: On}",
    initial_vars={"permit": 1, "motor": 1, "__forced_0": 0},
)
show("hot start", restored)
restored.cycle()
show("hot start, one cycle later", restored)

restored.cycle(["/Stop"])
show("after /Stop", restored)
