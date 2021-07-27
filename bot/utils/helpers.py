from typing import Any, Union


class DotDict(dict):
    """
    A `dict` subclass that implements dot notation
    """

    def _format_array(
        self,
        array: list,
        *,
        tuple_: bool = False
    ) -> Union[list, tuple]:
        data = [
            DotDict(element)
            if isinstance(element, dict)
            else self._format_list(element)
            if isinstance(element, list)
            else element
            for element in array
        ]

        return tuple(data) if tuple_ else list(data)

    def __getattr__(self, key: str) -> Any:
        try:
            value = self[key]
        except KeyError as e:
            raise AttributeError(e)

        if isinstance(value, dict):
            return DotDict(value)

        if isinstance(value, (list, tuple)):
            return self._format_array(
                value,
                tuple_=not isinstance(value, list)
            )

        return value

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

    def __delattr__(self, key: str) -> None:
        try:
            del self[key]
        except KeyError as e:
            raise AttributeError(e)

    def __repr__(self) -> str:
        return f"<DotDict {dict.__repr__(self)}>"
