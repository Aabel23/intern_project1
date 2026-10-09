"""Hand GPIO lines back so ANOTHER PROCESS can claim them.

WHY THIS EXISTS
    gpiozero's .close() is not enough on the lgpio backend, and its own
    LGPIOPin.close() says exactly why:

        # Closing is really just "resetting" the function of the pin;
        # we let the factory close deal with actually freeing stuff

    All close() does is re-claim the line as a pull-less input. The line
    stays claimed by this process: `gpioinfo` still reports it "[used]",
    and the next process to want it -- order/process_runner.py, started
    fresh for every drink -- dies with 'GPIO busy'.

    Only lgpio.gpio_free() releases it for real, short of closing the
    whole pin factory, which would take every other gpiozero device in
    the process down with it.

WHY IT MATTERS HERE MORE THAN ANYWHERE
    main.py runs store_gui, sync_menu and run_flow as threads in ONE
    long-lived process. Anything that process claims, it keeps until the
    service restarts -- so a single unfreed line silently breaks every
    order from then on.

BEST EFFORT BY DESIGN
    A pin that was never claimed, a backend that is not lgpio, a factory
    that was never built: none of those are errors. This is cleanup, and
    cleanup that raises is worse than cleanup that quietly does nothing.
"""

from __future__ import annotations

from collections.abc import Iterable


def free_gpio_line(number: int) -> bool:
    """Release one BCM line. True if lgpio actually let it go."""
    try:
        import lgpio
        from gpiozero import Device

        # Not ensure_pin_factory(): if nothing in this process has opened
        # a device, there is no handle and nothing to free, and building
        # a factory just to free a line we never claimed is backwards.
        factory = getattr(Device, "pin_factory", None)
        handle = getattr(factory, "_handle", None)

        if handle is None:
            return False

        lgpio.gpio_free(handle, int(number))
        return True
    except Exception:      # noqa: BLE001 - cleanup must never raise
        return False


def free_gpio_lines(numbers: Iterable[int]) -> list[int]:
    """Release several lines. Returns the ones lgpio actually let go."""
    return [
        number
        for number in numbers
        if free_gpio_line(number)
    ]
