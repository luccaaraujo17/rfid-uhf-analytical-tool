# -*- coding: utf-8 -*-
import os, sys
print("Python:",sys.version)
print("OPENEMS_INSTALL_PATH:",os.environ.get("OPENEMS_INSTALL_PATH"))
print("CSXCAD_INSTALL_PATH:",os.environ.get("CSXCAD_INSTALL_PATH"))
try:
    import CSXCAD
    import openEMS
    print("CSXCAD OK:",CSXCAD.ContinuousStructure())
    print("openEMS OK:",openEMS.openEMS())
    print("INSTALAÇÃO FUNCIONAL")
except Exception as exc:
    print("FALHA NA IMPORTAÇÃO:",repr(exc))
    raise SystemExit(1)
