from typing import Optional, Union, Sequence

import math

import numpy as np

import jax
from jax import numpy as jnp


__all__ = [
    "process_mask_axis",
    "is_maskable",
    "process_mask",
    "flatten",
    "unflatten",
    "get_mask",
    "masked_fill",
    "masked_sum",
    "masked_mean",
    "masked_min",
    "masked_max",
    "repeat_axis",
    "logsumexp",
    "logmeanexp",
    "apply_mask",
]


Axis = Union[int, Sequence[int]]
OptAxis = Optional[Axis]


def process_mask_axis(a_ndim, mask_ndim, mask_axis: OptAxis = None, non_mask_axis: OptAxis = None):
    """
    Process mask axis
    """

    if mask_axis is None and non_mask_axis is None:
        if a_ndim != mask_ndim:
            raise ValueError(
                f"Array and mask must have same dimension if mask_axis and non_mask_axis are not specified: "
                f"{a_ndim} != {mask_ndim}"
            )
        mask_axis = set(range(a_ndim))
        non_mask_axis = set()
    elif mask_axis is not None and non_mask_axis is None:
        mask_axis = [mask_axis] if isinstance(mask_axis, int) else mask_axis
        if len(mask_axis) != mask_ndim:
            raise ValueError(
                f"length of mask_axis must match mask.ndim: {len(mask_axis)} != {mask_ndim}"
            )
        mask_axis = set([d if d >= 0 else d + a_ndim for d in mask_axis])
        non_mask_axis = set(range(a_ndim)) - mask_axis

    elif mask_axis is None and non_mask_axis is not None:
        non_mask_axis = [non_mask_axis] if isinstance(non_mask_axis, int) else non_mask_axis
        if len(non_mask_axis) != a_ndim - mask_ndim:
            raise ValueError(
                f"length of non_mask_axis must match a.ndim - mask.ndim: "
                f"{len(non_mask_axis)} != {a_ndim - mask_ndim}"
            )
        non_mask_axis = set([d if d >= 0 else d + a_ndim for d in non_mask_axis])
        mask_axis = set(range(a_ndim)) - non_mask_axis

    else:
        raise ValueError("Only one of mask_axis and non_mask_axis can be specified")

    return tuple(mask_axis), tuple(non_mask_axis)


def is_maskable(a, mask, mask_axis: OptAxis = None, non_mask_axis: OptAxis = None):
    """
    Check if a mask is maskable to array.
    """

    mask_axis, non_mask_axis = process_mask_axis(a.ndim, mask.ndim, mask_axis, non_mask_axis)

    try:
        target_a_shape = tuple([a.shape[d] for d in mask_axis])
        maskable = (np.broadcast_shapes(mask.shape, target_a_shape) == target_a_shape)
    except ValueError:
        maskable = False

    return maskable


def process_mask(a, mask, mask_axis: OptAxis = None, non_mask_axis: OptAxis = None):
    """
    Process a mask.
    """

    mask_axis, non_mask_axis = process_mask_axis(a.ndim, mask.ndim, mask_axis, non_mask_axis)

    try:
        target_a_shape = tuple([a.shape[d] for d in mask_axis])
        maskable = (np.broadcast_shapes(mask.shape, target_a_shape) == target_a_shape)
    except ValueError:
        maskable = False

    if not maskable:
        raise ValueError(
            f"Mask shape must broadcastable to array along target axis: "
            f"array shape {a.shape}, mask shape {mask.shape}, target axis {mask_axis}"
        )

    mask = jnp.expand_dims(mask, axis=non_mask_axis)
    return mask


def flatten(a, start: Optional[int] = None, stop: Optional[int] = None):
    """
    Flatten an array.
    """

    start = 0      if start is None else start if start >= 0 else start + a.ndim
    stop  = a.ndim if stop  is None else stop  if stop  >= 0 else stop  + a.ndim

    original_shape = a.shape[start:stop]
    flatten_size = math.prod(original_shape)
    meta = (original_shape, flatten_size)

    a = jnp.reshape(a, (*a.shape[:start], flatten_size, *a.shape[stop:]))
    return a, meta


def unflatten(a, meta, axis: int):
    """
    Unflatten an array.
    """

    axis = axis if axis >= 0 else axis + a.ndim
    original_shape, flatten_size = meta

    if a.shape[axis] != flatten_size:
        raise ValueError(f"Size mismatch: {a.shape[axis]} != {flatten_size}")

    a = jnp.reshape(a, (*a.shape[:axis], *original_shape, *a.shape[axis+1:]))
    return a


def get_mask(n: int, start: int = 0, stop: int = None):
    """
    Get a mask of shape (n,) which filled ones at index [start, stop).
    """

    stop = n if stop is None else stop
    mask = (start <= jnp.arange(n)) & (jnp.arange(n) < stop)
    return mask


def masked_fill(
    a,
    mask,
    mask_axis: OptAxis = None,
    non_mask_axis: OptAxis = None,
    fill_value: int = 0,
):
    """
    Apply a mask to an array along a given axis.
    """

    mask = process_mask(a, mask, mask_axis, non_mask_axis)
    a = jnp.where(mask, a, fill_value)
    return a


def masked_sum(
    a,
    mask,
    axis: OptAxis = None,
    mask_axis: OptAxis = None,
    non_mask_axis: OptAxis = None,
    keepdims: bool = False,
):
    """
    Sum a masked array along a given axis.
    """

    mask = process_mask(a, mask, mask_axis, non_mask_axis)
    a = jnp.sum(a, axis=axis, keepdims=keepdims, where=mask)
    return a


def masked_mean(
    a,
    mask,
    axis: OptAxis = None,
    mask_axis: OptAxis = None,
    non_mask_axis: OptAxis = None,
    keepdims: bool = False,
):
    """
    Mean a masked array along a given axis.
    """

    mask = process_mask(a, mask, mask_axis, non_mask_axis)
    a = jnp.mean(a, axis=axis, keepdims=keepdims, where=mask)
    return a


def masked_min(
    a,
    mask,
    axis: OptAxis = None,
    mask_axis: OptAxis = None,
    non_mask_axis: OptAxis = None,
    keepdims: bool = False,
):
    """
    Minimum of a masked array along a given axis.
    """

    mask = process_mask(a, mask, mask_axis, non_mask_axis)
    a = jnp.min(a, axis=axis, keepdims=keepdims, where=mask, initial=jnp.inf)
    return a


def masked_max(
    a,
    mask,
    axis: OptAxis = None,
    mask_axis: OptAxis = None,
    non_mask_axis: OptAxis = None,
    keepdims: bool = False,
):
    """
    Maximum of a masked array along a given axis.
    """

    mask = process_mask(a, mask, mask_axis, non_mask_axis)
    a = jnp.max(a, axis=axis, keepdims=keepdims, where=mask, initial=-jnp.inf)
    return a


def repeat_axis(a, repeats: Union[int, Sequence[int]], axis: Axis):
    """
    Repeat an array along a given axis.
    """

    repeats = [repeats] if isinstance(repeats, int) else repeats
    axis    = [axis]    if isinstance(axis,    int) else axis

    if len(repeats) != len(axis):
        raise ValueError(f"length of repeats must match length of axis: {len(repeats)} != {len(axis)}")

    a = jnp.expand_dims(a, axis=axis)
    for r, d in zip(repeats, axis):
        a = jnp.repeat(a, repeats=r, axis=d)
    return a


logsumexp = jax.nn.logsumexp


def logmeanexp(a, axis: Axis = None, b = None, keepdims: bool = False, return_sign: bool = False):
    """
    Log 1/N Sum Exp.
    """

    if axis is None:
        divider = a.size
    elif isinstance(axis, int):
        divider = a.shape[axis]
    else:
        divider = math.prod([a.shape[d] for d in range(axis)])

    a = jax.nn.logsumexp(a, axis=axis, b=b, keepdims=keepdims, return_sign=return_sign) \
      - math.log(divider)

    return a


apply_mask = masked_fill
