"""Stores the options available for element classes and properties."""


ELEMENT_FIELDS = {
    "Lines": [
        {
            "name": "Currents",
            "options": [
                "phase_terminal",
            ]
        },
        {
            "name": "Powers",
            "options": [
                "phase_terminal",
            ]
        },
        {
            "name": "NormalAmps",
            "options": [],
        },
        {
            "name": "Enabled",
            "options": [],
        },
    ],
    "Buses": [
    ]
}


class ElementOptions:
    """Stores the options available for element classes and properties."""
    def __init__(self, data=None):
        if data is None:
            data = ELEMENT_FIELDS
        self._element_classes = {}
        for elem_class, properties in data.items():
            options = {}
            for prop in properties:
                options[prop["name"]] = prop["options"]
            self._element_classes[elem_class] = options

    def is_option_valid(self, element_class, prop, option):
        """Returns True if the option is valid for the class and property.

        Returns
        -------
        True

        """
        return option in self.list_options(element_class, prop)

    def list_options(self, element_class, prop):
        """List the options available for a class and property.

        Returns
        -------
        list

        """
        if element_class not in self._element_classes:
            raise Exception(f"class={element_class} is not stored")
        if prop not in self._element_classes[element_class]:
            raise Exception(
                f"class={element_class} property={prop} is not stored"
            )
        return self._element_classes[element_class][prop][:]
