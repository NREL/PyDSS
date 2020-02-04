ELEMENT_FIELDS = {
    "Lines": [
        {
            "names": ["Currents", "Powers", 'Voltages', 'PhaseLosses'],
            "options": [
                "phase_terminal",
            ],
        },
        {
            "names": ["SeqVoltages", "SeqPowers", 'SeqCurrents', 'VoltagesMagAng', 'CurrentsMagAng'],
            "options": [
                "phase_terminal", "mag_ang"
            ],
        },
    ],
    "Transformer": [
        {
            "names": ["Currents", "Powers", 'Voltages', 'PhaseLosses'],
            "options": [
                "phase_terminal",
            ],
        },
        {
            "names": ["SeqVoltages", "SeqPowers", 'SeqCurrents', 'VoltagesMagAng', 'CurrentsMagAng'],
            "options": [
                "phase_terminal", "mag_ang"
            ],
        },
        {
            "names": ["taps", "maxtap", 'mintap', 'numtaps', 'kv', 'kva'],
            "options": [
                "wdg",
            ],
        },
    ],
    "Generators": [
            {
                "names": ["Currents", "Powers", 'Voltages', 'PhaseLosses'],
                "options": [
                    "phase_terminal",
                ],
            },
            {
                "names": ["SeqVoltages", "SeqPowers", 'SeqCurrents', 'VoltagesMagAng', 'CurrentsMagAng'],
                "options": [
                    "phase_terminal", "mag_ang"
                ],
            },
        ],
    "PVSystems": [
                {
                    "names": ["Currents", "Powers", 'Voltages', 'PhaseLosses'],
                    "options": [
                        "phase_terminal",
                    ],
                },
                {
                    "names": ["SeqVoltages", "SeqPowers", 'SeqCurrents', 'VoltagesMagAng', 'CurrentsMagAng'],
                    "options": [
                        "phase_terminal", "mag_ang"
                    ],
                },
            ],
    "Loads": [
                {
                    "names": ["Currents", "Powers", 'Voltages', 'PhaseLosses'],
                    "options": [
                        "phase_terminal",
                    ],
                },
                {
                    "names": ["SeqVoltages", "SeqPowers", 'SeqCurrents', 'VoltagesMagAng', 'CurrentsMagAng'],
                    "options": [
                        "phase_terminal", "mag_ang"
                    ],
                },
            ],
    "Storages": [
        {
            "names": ["Currents", "Powers", 'Voltages', 'PhaseLosses'],
            "options": [
                "phase_terminal",
            ],
        },
        {
            "names": ["SeqVoltages", "SeqPowers", 'SeqCurrents', 'VoltagesMagAng', 'CurrentsMagAng'],
            "options": [
                "phase_terminal", "mag_ang"
            ],
        },
    ],
    "Capacitors": [
            {
                "names": ["Currents", "Powers", 'Voltages', 'PhaseLosses'],
                "options": [
                    "phase_terminal",
                ],
            },
            {
                "names": ["SeqVoltages", "SeqPowers", 'SeqCurrents', 'VoltagesMagAng', 'CurrentsMagAng'],
                "options": [
                    "phase_terminal", "mag_ang"
                ],
            },
{
                "names": ["states", 'open', 'close'],
                "options": [
                ],
            },
        ],
    "Meters": [
                {
                    "names": ["AllocFactors"],
                    "options": [
                        "phase_terminal",
                    ],
                }
            ],
}
