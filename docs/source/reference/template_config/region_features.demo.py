import os
import tempfile

from pyfcstm.render import StateMachineCodeRenderer


def check(label, config_text):
    with tempfile.TemporaryDirectory() as work:
        with open(os.path.join(work, "config.yaml"), "w") as stream:
            stream.write(config_text)
        try:
            renderer = StateMachineCodeRenderer(work)
        except ValueError as err:
            print("%s -> ValueError: %s" % (label, str(err).replace(work, "<work>")))
        else:
            print("%s -> accepted, features = %s" % (label, sorted(renderer.features)))


check("(no features key)", "{}\n")
check("features: [region]", "features: [region]\n")
check("features: []", "features: []\n")
check("features:", "features:\n")
check("features: region", "features: region\n")
check("features: {region: true}", "features: {region: true}\n")
check("features: [cloud]", "features: [cloud]\n")
check("features: [Region]", "features: [Region]\n")
check("features: [region, region]", "features: [region, region]\n")
check("features: [1]", "features: [1]\n")
check("features: [null]", "features: [null]\n")
