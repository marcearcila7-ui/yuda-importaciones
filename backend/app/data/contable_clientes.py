"""Foto fija de los clientes de Yuda Contable (app aparte), para la
herramienta de importación de la Fase 2.

Solo nombre/sigla/país/teléfono — nunca datos financieros. No es una
sincronización en vivo: es una lista que se actualiza a mano (pidiéndomela de
nuevo) cuando haga falta traer clientes nuevos de esa app.
"""

CONTABLE_CLIENTES: list[dict[str, str | None]] = [
    {"sigla": "ABM", "nombre": "Angie Bedoya", "pais": "Colombia", "telefono": "+57 302 3085803"},
    {"sigla": "AD", "nombre": "Juan", "pais": "Colombia", "telefono": "32056765400"},
    {"sigla": "AJ", "nombre": "Adrina Ramirez", "pais": "Colombia", "telefono": "3206242943"},
    {"sigla": "AMA", "nombre": None, "pais": None, "telefono": None},
    {"sigla": "BZ", "nombre": "Alejandro Betancur", "pais": None, "telefono": "3005060872"},
    {"sigla": "CC", "nombre": None, "pais": None, "telefono": None},
    {"sigla": "CJ", "nombre": "Camila Beltran", "pais": "Colombia", "telefono": "3104706900"},
    {"sigla": "DC", "nombre": "Alejandro Giraldo", "pais": "Costa Rica", "telefono": "61120105"},
    {"sigla": "DS", "nombre": "Daniela Sánchez", "pais": "Colombia", "telefono": "3147998325"},
    {"sigla": "EMPO", "nombre": "Ender Portillo", "pais": "Colombia", "telefono": "3007711658"},
    {"sigla": "ESP", "nombre": "Camila Espectanas", "pais": None, "telefono": "3106299259"},
    {"sigla": "EV", "nombre": "Luis Estada", "pais": None, "telefono": "3148889820"},
    {"sigla": "FL", "nombre": "Nathalia Golzales", "pais": None, "telefono": "+57 313 2635602"},
    {"sigla": "FULL", "nombre": "Lina Ortega", "pais": None, "telefono": "+57 320 5109743"},
    {"sigla": "HG", "nombre": "Claudia Cardona", "pais": "Colombia", "telefono": "3105314009"},
    {"sigla": "HN", "nombre": "Hernán D.", "pais": "Colombia", "telefono": "3012691264"},
    {"sigla": "IN", "nombre": "Indi Godoy", "pais": "Colombia", "telefono": "3118551534"},
    {"sigla": "ISN", "nombre": "Camilo Sánchez", "pais": "Colombia", "telefono": "3147989732"},
    {"sigla": "JACK", "nombre": "Jackelune Cliente", "pais": "Colombia", "telefono": "3193294684"},
    {"sigla": "JC", "nombre": "Juan Carlos Cliente", "pais": "Colombia", "telefono": "3127604147"},
    {"sigla": "JND", "nombre": "Alejandro Giraldo", "pais": "Costa Rica", "telefono": "61120105"},
    {"sigla": "KAES", "nombre": "Esteban Obyrne", "pais": "Colombia", "telefono": "3012845062"},
    {"sigla": "KLY", "nombre": "Willian Cliente", "pais": None, "telefono": "3223928284"},
    {"sigla": "LE", "nombre": "Luis", "pais": None, "telefono": None},
    {"sigla": "LF", "nombre": "Erik Colombia", "pais": "Colombia", "telefono": "3505820523"},
    {"sigla": "LG", "nombre": "Jorge Arias", "pais": "Colombia", "telefono": "3206909008"},
    {"sigla": "LL", "nombre": "Lluvia D Estrellas", "pais": None, "telefono": "3112210707"},
    {"sigla": "ME", "nombre": "Andres R", "pais": None, "telefono": None},
    {"sigla": "MISS", "nombre": "Yilliam Pineda", "pais": "Colombia", "telefono": "3217247519"},
    {"sigla": "MM", "nombre": "Alejandro Giraldo", "pais": None, "telefono": "61120105"},
    {"sigla": "MN", "nombre": "Sergio Cliente", "pais": "Colombia", "telefono": "3206394403"},
    {"sigla": "MT", "nombre": "Fabian Castellanos", "pais": "Colombia", "telefono": "3160504650"},
    {"sigla": "NATY", "nombre": None, "pais": None, "telefono": None},
    {"sigla": "OG", "nombre": "Oscar Garcia", "pais": None, "telefono": None},
    {"sigla": "OH", "nombre": "Laura Chaverra", "pais": None, "telefono": "3145071814"},
    {"sigla": "OLA", "nombre": None, "pais": None, "telefono": None},
    {"sigla": "PP", "nombre": None, "pais": None, "telefono": None},
    {"sigla": "QR", "nombre": None, "pais": None, "telefono": None},
    {"sigla": "SR", "nombre": "Sergio Cliente", "pais": "Colombia", "telefono": "3206394403"},
    {"sigla": "ST", "nombre": "Angie Bedoya Purpure", "pais": "Colombia", "telefono": "3023085803"},
    {"sigla": "TAD", "nombre": None, "pais": None, "telefono": None},
    {"sigla": "WG", "nombre": None, "pais": None, "telefono": None},
    {"sigla": "WL", "nombre": None, "pais": None, "telefono": None},
    {"sigla": "ZL", "nombre": None, "pais": None, "telefono": None},
]
