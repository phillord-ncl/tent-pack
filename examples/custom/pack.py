from tent_pack import Pack


def build():
    pack = Pack(format=1, name="pack.py demo").exclude("pack.py")
    pack.require("main.py")
    pack.check(lambda ctx: "no TODOs" if "TODO" in ctx.path("main.py").read_text() else None,
               name="no TODO left in main.py")
    return pack
