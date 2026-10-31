#include <stdint.h>

#define TRACE_TICK_RATE 10000
typedef uint32_t TraceTickType_t;
volatile extern TraceTickType_t customTraceTimerTick;
static inline TraceTickType_t GetTraceTick()
{
  return customTraceTimerTick;
}
