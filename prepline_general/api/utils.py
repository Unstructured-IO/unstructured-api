from typing import TypeVar, Union, List, Optional, Generic, get_origin, get_args

T = TypeVar("T")


def _return_casted_first_element(value: list[str], origin_class: type) -> T | None:
    """Return the first element of a list cast to a type T, or None if the list is empty

    Args:
        value (list[str]): list of strings
        origin_class (type): type to cast the first element to. Should be one of simple types

    Returns:
        T | None: first element cast to a type T, or None if the list is empty
    """
    value = next(iter(value), None)
    if value is not None:
        if origin_class == int or origin_class == float or origin_class == bool:
            return origin_class(value)
    return value


def _extract_inner_list_casted_to_specific_type(
    value: list[list], container_elems_class: type[T]
) -> list[T]:
    """If a list contains inner list - extract it and cast its elements to a specific type
    Returns the original list if it doesn't contain inner list.

    Args:
        value (list[list]): list of lists
        container_elems_class (type[T]): type to cast the inner list elements to.

    Returns:
        list[T]: list of elements cast to a specific type or the original list
            if it doesn't contain inner list.
    """
    if value and isinstance(value[0], list):
        inner_list = next(iter(value))
        if isinstance(inner_list, list):
            return [container_elems_class(elem) for elem in inner_list]
    return value


class SmartValueParser(Generic[T]):
    """Class handle api parameters that are passed in form of a specific value or as a list of strings from which
    the first element is used, cast to a proper type
    Should be parametrized with a type to which the value should be casted.

    Examples:
        SmartValueParser[int]().value_or_first_element(value)
        SmartValueParser[list[int]]().value_or_first_element(value)
    """

    def value_or_first_element(self, value: Union[T, List[str]]) -> Optional[T]:
        """If value is a list, return the first element cast to a type T, otherwise return the value itself

        Args:
            value (Union[T, List[str]]): value to cast to a type T or return as is
        """
        origin_class, container_elems_class = self._get_origin_container_classes()
        if isinstance(value, list) and not isinstance(value, origin_class):
            return _return_casted_first_element(value, origin_class)
        elif isinstance(value, list) and origin_class == list:
            return _extract_inner_list_casted_to_specific_type(value, container_elems_class)
        return value

    def _get_origin_container_classes(self) -> tuple[type, type | None]:
        """Extracts class (and container class if it's a list) from a type hint

        Returns:
            tuple[type, type | None]: class and container class of the type hint
        """
        type_info = self.__orig_class__.__args__[0]
        origin_class = get_origin(type_info)
        if origin_class is None:
            # it's a basic type like int or bool - return it and no container class
            return type_info, None
        origin_args = get_args(type_info)
        container_elems_class = origin_args[0] if origin_args else None
        return origin_class, container_elems_class
