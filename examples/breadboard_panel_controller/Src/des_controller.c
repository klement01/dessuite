#include "des_controller.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "FreeRTOS.h"
#include "FreeRTOSConfig.h"
#include "portmacro.h"
#include "projdefs.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"
#include "timers.h"

#if (true)
#define CORE_ENABLE_TRACE
#endif

#if (true)
#define CORE_ENABLE_CUSTOM_TRACE_CLOCK
#endif

#ifdef CORE_ENABLE_TRACE
#include <stdio.h>
#endif

/** Module includes and defines. **/

#include "main.h"


/** Core data (defines, types and constants). **/

/* User parameters. */

#define CORE_EVENT_QUEUE_SIZE (16)

#define CORE_EVENT_LOOP_TASK_NAME ("DessuiteEventLoop")
#define CORE_EVENT_LOOP_TASK_SDEPTH (configMINIMAL_STACK_SIZE)
#define CORE_EVENT_LOOP_TASK_PRIORITY (configMAX_PRIORITIES - 1)

#define CORE_SCHEDULE_COMMAND_TASK_NAME ("DessuiteScheduleCommand")
#define CORE_SCHEDULE_COMMAND_TASK_PRIORITY (configMAX_PRIORITIES - 2)

#ifdef CORE_ENABLE_TRACE

#define CORE_TRACE_QUEUE_SIZE (32)

#define CORE_TRACE_LOOP_TASK_NAME ("DessuiteTraceLoop")
#define CORE_TRACE_LOOP_TASK_SDEPTH (configMINIMAL_STACK_SIZE)
#define CORE_TRACE_LOOP_TASK_PRIORITY (1)

#endif

/* Petri Net definition. */

#define CORE_EVENT_COUNT (14)
#define CORE_COMMAND_COUNT (13)
#define CORE_PLACE_COUNT (13)

typedef uint8_t EventIdx_t;
typedef uint8_t PlaceIdx_t;
typedef uint8_t CommandIdx_t;
typedef uint8_t PlaceMarking_t;
typedef int8_t ArcWeight_t;

enum EventIdx : EventIdx_t
{
  EVENT_0, // b1_delay
  EVENT_1, // b1_press
  EVENT_2, // cycle_off_finish
  EVENT_3, // cycle_off_start
  EVENT_4, // cycle_on_finish
  EVENT_5, // cycle_on_start
  EVENT_6, // g1_cycle_off
  EVENT_7, // g1_cycle_on
  EVENT_8, // g1_turn_off
  EVENT_9, // r1_cycle_off
  EVENT_10, // r1_cycle_on
  EVENT_11, // r1_turn_off
  EVENT_12, // w1_turn_off
  EVENT_13, // w1_turn_on
  EVENT_SCHEDULED_COMMAND
};

struct RichEvent
{
  EventIdx_t idx;
  TickType_t tick;
};

struct RichCommand
{
  CommandIdx_t idx;
  TickType_t tick;
};

struct Place
{
  PlaceMarking_t markings;
};

struct TransitionArc
{
  const PlaceIdx_t placeIdx;
  const ArcWeight_t weight;
};

enum EventStatus : uint8_t
{
  EVENT_STATUS_ENABLED,
  EVENT_STATUS_DISABLED_STRUCTURALLY,
  EVENT_STATUS_DISABLED_TOO_SOON,
  EVENT_STATUS_DISABLED_TOO_LATE
};

struct EventTransition
{
  const int8_t inhibitorArcsCount;
  const int8_t inputArcsCount;
  const int8_t deltaArcsCount;
  const int8_t affectedTransitionsCount;
  const struct TransitionArc *inhibitorArcs;
  const struct TransitionArc *inputArcs;
  const struct TransitionArc *deltaArcs;
  const EventIdx_t *affectedTransitions;
  const TickType_t intervalLowerLimit;
  const TickType_t intervalUpperLimit;
};

const struct TransitionArc EVENT_0_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_0_INPUT_ARCS[1] = {
  {0, 1}
};
const struct TransitionArc EVENT_0_DELTA_ARCS[2] = {
  {0, -1},
  {1, 1}
};
const EventIdx_t EVENT_0_AFFECTED_TRANSITIONS[8] = {0, 1, 2, 3, 4, 5, 12, 13};

const struct TransitionArc EVENT_1_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_1_INPUT_ARCS[1] = {
  {1, 1}
};
const struct TransitionArc EVENT_1_DELTA_ARCS[2] = {
  {0, 1},
  {1, -1}
};
const EventIdx_t EVENT_1_AFFECTED_TRANSITIONS[8] = {0, 1, 2, 3, 4, 5, 12, 13};

const struct TransitionArc EVENT_2_INHIBITOR_ARCS[1] = {
  {0, 1}
};
const struct TransitionArc EVENT_2_INPUT_ARCS[1] = {
  {2, 1}
};
const struct TransitionArc EVENT_2_DELTA_ARCS[2] = {
  {2, -1},
  {3, 1}
};
const EventIdx_t EVENT_2_AFFECTED_TRANSITIONS[2] = {2, 5};

const struct TransitionArc EVENT_3_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_3_INPUT_ARCS[3] = {
  {0, 1},
  {4, 1},
  {6, 1}
};
const struct TransitionArc EVENT_3_DELTA_ARCS[3] = {
  {2, 1},
  {4, -1},
  {6, -1}
};
const EventIdx_t EVENT_3_AFFECTED_TRANSITIONS[8] = {2, 3, 6, 7, 8, 9, 10, 11};

const struct TransitionArc EVENT_4_INHIBITOR_ARCS[1] = {
  {0, 1}
};
const struct TransitionArc EVENT_4_INPUT_ARCS[1] = {
  {5, 1}
};
const struct TransitionArc EVENT_4_DELTA_ARCS[2] = {
  {5, -1},
  {6, 1}
};
const EventIdx_t EVENT_4_AFFECTED_TRANSITIONS[2] = {3, 4};

const struct TransitionArc EVENT_5_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_5_INPUT_ARCS[2] = {
  {0, 1},
  {3, 1}
};
const struct TransitionArc EVENT_5_DELTA_ARCS[3] = {
  {3, -1},
  {4, 1},
  {5, 1}
};
const EventIdx_t EVENT_5_AFFECTED_TRANSITIONS[9] = {3, 4, 5, 6, 7, 8, 9, 10, 11};

const struct TransitionArc EVENT_6_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_6_INPUT_ARCS[2] = {
  {4, 1},
  {8, 1}
};
const struct TransitionArc EVENT_6_DELTA_ARCS[2] = {
  {7, 1},
  {8, -1}
};
const EventIdx_t EVENT_6_AFFECTED_TRANSITIONS[3] = {6, 7, 8};

const struct TransitionArc EVENT_7_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_7_INPUT_ARCS[2] = {
  {4, 1},
  {7, 1}
};
const struct TransitionArc EVENT_7_DELTA_ARCS[2] = {
  {7, -1},
  {8, 1}
};
const EventIdx_t EVENT_7_AFFECTED_TRANSITIONS[3] = {6, 7, 8};

const struct TransitionArc EVENT_8_INHIBITOR_ARCS[1] = {
  {4, 1}
};
const struct TransitionArc EVENT_8_INPUT_ARCS[1] = {
  {8, 1}
};
const struct TransitionArc EVENT_8_DELTA_ARCS[2] = {
  {7, 1},
  {8, -1}
};
const EventIdx_t EVENT_8_AFFECTED_TRANSITIONS[3] = {6, 7, 8};

const struct TransitionArc EVENT_9_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_9_INPUT_ARCS[2] = {
  {4, 1},
  {10, 1}
};
const struct TransitionArc EVENT_9_DELTA_ARCS[2] = {
  {9, 1},
  {10, -1}
};
const EventIdx_t EVENT_9_AFFECTED_TRANSITIONS[3] = {9, 10, 11};

const struct TransitionArc EVENT_10_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_10_INPUT_ARCS[2] = {
  {4, 1},
  {9, 1}
};
const struct TransitionArc EVENT_10_DELTA_ARCS[2] = {
  {9, -1},
  {10, 1}
};
const EventIdx_t EVENT_10_AFFECTED_TRANSITIONS[3] = {9, 10, 11};

const struct TransitionArc EVENT_11_INHIBITOR_ARCS[1] = {
  {4, 1}
};
const struct TransitionArc EVENT_11_INPUT_ARCS[1] = {
  {10, 1}
};
const struct TransitionArc EVENT_11_DELTA_ARCS[2] = {
  {9, 1},
  {10, -1}
};
const EventIdx_t EVENT_11_AFFECTED_TRANSITIONS[3] = {9, 10, 11};

const struct TransitionArc EVENT_12_INHIBITOR_ARCS[1] = {
  {0, 1}
};
const struct TransitionArc EVENT_12_INPUT_ARCS[1] = {
  {12, 1}
};
const struct TransitionArc EVENT_12_DELTA_ARCS[2] = {
  {11, 1},
  {12, -1}
};
const EventIdx_t EVENT_12_AFFECTED_TRANSITIONS[2] = {12, 13};

const struct TransitionArc EVENT_13_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_13_INPUT_ARCS[2] = {
  {0, 1},
  {11, 1}
};
const struct TransitionArc EVENT_13_DELTA_ARCS[2] = {
  {11, -1},
  {12, 1}
};
const EventIdx_t EVENT_13_AFFECTED_TRANSITIONS[2] = {12, 13};

const struct EventTransition CORE_EVENT_TRANSITIONS[CORE_EVENT_COUNT] =
{
  {0, 1, 2, 8, EVENT_0_INHIBITOR_ARCS, EVENT_0_INPUT_ARCS, EVENT_0_DELTA_ARCS, EVENT_0_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(200U)+1, pdMS_TO_TICKS(210U)-1},
  {0, 1, 2, 8, EVENT_1_INHIBITOR_ARCS, EVENT_1_INPUT_ARCS, EVENT_1_DELTA_ARCS, EVENT_1_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {1, 1, 2, 2, EVENT_2_INHIBITOR_ARCS, EVENT_2_INPUT_ARCS, EVENT_2_DELTA_ARCS, EVENT_2_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {0, 3, 3, 8, EVENT_3_INHIBITOR_ARCS, EVENT_3_INPUT_ARCS, EVENT_3_DELTA_ARCS, EVENT_3_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {1, 1, 2, 2, EVENT_4_INHIBITOR_ARCS, EVENT_4_INPUT_ARCS, EVENT_4_DELTA_ARCS, EVENT_4_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {0, 2, 3, 9, EVENT_5_INHIBITOR_ARCS, EVENT_5_INPUT_ARCS, EVENT_5_DELTA_ARCS, EVENT_5_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {0, 2, 2, 3, EVENT_6_INHIBITOR_ARCS, EVENT_6_INPUT_ARCS, EVENT_6_DELTA_ARCS, EVENT_6_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(200U)+1, pdMS_TO_TICKS(210U)-1},
  {0, 2, 2, 3, EVENT_7_INHIBITOR_ARCS, EVENT_7_INPUT_ARCS, EVENT_7_DELTA_ARCS, EVENT_7_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(200U)+1, pdMS_TO_TICKS(210U)-1},
  {1, 1, 2, 3, EVENT_8_INHIBITOR_ARCS, EVENT_8_INPUT_ARCS, EVENT_8_DELTA_ARCS, EVENT_8_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), pdMS_TO_TICKS(10U)-1},
  {0, 2, 2, 3, EVENT_9_INHIBITOR_ARCS, EVENT_9_INPUT_ARCS, EVENT_9_DELTA_ARCS, EVENT_9_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(500U)+1, pdMS_TO_TICKS(510U)-1},
  {0, 2, 2, 3, EVENT_10_INHIBITOR_ARCS, EVENT_10_INPUT_ARCS, EVENT_10_DELTA_ARCS, EVENT_10_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(500U)+1, pdMS_TO_TICKS(510U)-1},
  {1, 1, 2, 3, EVENT_11_INHIBITOR_ARCS, EVENT_11_INPUT_ARCS, EVENT_11_DELTA_ARCS, EVENT_11_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), pdMS_TO_TICKS(10U)-1},
  {1, 1, 2, 2, EVENT_12_INHIBITOR_ARCS, EVENT_12_INPUT_ARCS, EVENT_12_DELTA_ARCS, EVENT_12_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), pdMS_TO_TICKS(10U)-1},
  {0, 2, 2, 2, EVENT_13_INHIBITOR_ARCS, EVENT_13_INPUT_ARCS, EVENT_13_DELTA_ARCS, EVENT_13_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), pdMS_TO_TICKS(10U)-1},
};


/** Inter-task communication, available to modules. **/

QueueHandle_t EventQueue;

static inline void NewIncomingEventISR(EventIdx_t eventIdx, TickType_t tick, BaseType_t *xHigherPriorityTaskWoken)
{
  struct RichEvent incomingEvent = { .idx = eventIdx, .tick = tick };
  configASSERT(pdPASS == xQueueSendToBackFromISR(EventQueue, &incomingEvent, xHigherPriorityTaskWoken));
}


/** Module data (defines, types and constants). **/




/** Module variables. **/




/** Module function definitions. **/




/** Module input interface functions. **/

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
  const TickType_t tick = xTaskGetTickCountFromISR();
  BaseType_t xHigherPriorityTaskWoken = pdFALSE;
  switch (GPIO_Pin)
  {
    case BUTTON_1_Pin:
      NewIncomingEventISR(EVENT_1, tick, &xHigherPriorityTaskWoken);
      break;
  }
  portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}


/** Module output interface functions. **/




/** Core command handler. */

struct Command
{
  const enum EventIdx eventIdx;
  const void (*handler)(void);
};

void EVENT_0_COMMAND_HANDLER(void)
{
}
void EVENT_13_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_WHITE_1_GPIO_Port, LED_WHITE_1_Pin, GPIO_PIN_RESET);
}
void EVENT_12_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_WHITE_1_GPIO_Port, LED_WHITE_1_Pin, GPIO_PIN_SET);
}
void EVENT_5_COMMAND_HANDLER(void)
{
}
void EVENT_4_COMMAND_HANDLER(void)
{
}
void EVENT_3_COMMAND_HANDLER(void)
{
}
void EVENT_2_COMMAND_HANDLER(void)
{
}
void EVENT_10_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_RED_1_GPIO_Port, LED_RED_1_Pin, GPIO_PIN_RESET);
}
void EVENT_9_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_RED_1_GPIO_Port, LED_RED_1_Pin, GPIO_PIN_SET);
}
void EVENT_11_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_RED_1_GPIO_Port, LED_RED_1_Pin, GPIO_PIN_SET);
}
void EVENT_7_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_GREEN_1_GPIO_Port, LED_GREEN_1_Pin, GPIO_PIN_RESET);
}
void EVENT_6_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_GREEN_1_GPIO_Port, LED_GREEN_1_Pin, GPIO_PIN_SET);
}
void EVENT_8_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_GREEN_1_GPIO_Port, LED_GREEN_1_Pin, GPIO_PIN_SET);
}

const struct Command CORE_COMMANDS[CORE_COMMAND_COUNT] =
{
  {0, EVENT_0_COMMAND_HANDLER},
  {13, EVENT_13_COMMAND_HANDLER},
  {12, EVENT_12_COMMAND_HANDLER},
  {5, EVENT_5_COMMAND_HANDLER},
  {4, EVENT_4_COMMAND_HANDLER},
  {3, EVENT_3_COMMAND_HANDLER},
  {2, EVENT_2_COMMAND_HANDLER},
  {10, EVENT_10_COMMAND_HANDLER},
  {9, EVENT_9_COMMAND_HANDLER},
  {11, EVENT_11_COMMAND_HANDLER},
  {7, EVENT_7_COMMAND_HANDLER},
  {6, EVENT_6_COMMAND_HANDLER},
  {8, EVENT_8_COMMAND_HANDLER}
};


/** Log functions. **/

#ifdef CORE_ENABLE_TRACE

volatile bool usingNativeTraceTick = false;

__weak TraceTickType_t GetTraceTick()
{
  usingNativeTraceTick = true;
  return (TraceTickType_t)xTaskGetTickCount();
}

__weak TickType_t GetTraceTickRate()
{
  GetTraceTick();
  configASSERT(usingNativeTraceTick);
  return configTICK_RATE_HZ;
}

typedef uint8_t TraceType_t;

enum TraceType : TraceType_t
{
  TRACE_TYPE_TICK_RATE                             = (1),
  TRACE_TYPE_NET_START_TICK                        = (2),
  TRACE_TYPE_INCOMING_EVENT_ACCEPTED               = (3),
  TRACE_TYPE_INCOMING_EVENT_DROPPED_STRUCTURALLY   = (4),
  TRACE_TYPE_INCOMING_EVENT_DROPPED_TOO_SOON       = (5),
  TRACE_TYPE_INCOMING_EVENT_DROPPED_TOO_LATE       = (6),
  TRACE_TYPE_OUTGOING_COMMAND_ACCEPTED             = (7),
  TRACE_TYPE_OUTGOING_COMMAND_DROPPED_STRUCTURALLY = (8),
  TRACE_TYPE_OUTGOING_COMMAND_DROPPED_TOO_SOON     = (9),
  TRACE_TYPE_OUTGOING_COMMAND_DROPPED_TOO_LATE     = (10),
  TRACE_TYPE_OUTGOING_COMMAND_QUEUED               = (12),
  TRACE_TYPE_OUTGOING_COMMAND_STARTED              = (13),
  TRACE_TYPE_OUTGOING_COMMAND_FINISHED             = (14),
  TRACE_TYPE_COMMAND_NOT_CHOSEN_TOO_LATE           = (15)
};

struct Trace
{
  TraceTickType_t traceTick;
  TraceType_t traceType;
  union {
    struct RichEvent event;
    TickType_t startTick;
  } data;
};

TaskHandle_t TaskTraceLoopHandle;
QueueHandle_t TraceQueue;

void TaskTraceLoop(void*)
{
  for (;;)
  {
    struct Trace trace;
    configASSERT(pdPASS == xQueueReceive(TraceQueue, &trace, portMAX_DELAY));

    printf("%lu\t%u\t", trace.traceTick, trace.traceType);

    switch (trace.traceType)
    {
      case TRACE_TYPE_TICK_RATE:
        printf("%lu\t%lu", (TraceTickType_t)configTICK_RATE_HZ, GetTraceTickRate());
        break;
      case TRACE_TYPE_NET_START_TICK:
        printf("%lu",  trace.data.startTick);
        break;
      case TRACE_TYPE_INCOMING_EVENT_ACCEPTED:
      case TRACE_TYPE_INCOMING_EVENT_DROPPED_STRUCTURALLY:
      case TRACE_TYPE_INCOMING_EVENT_DROPPED_TOO_SOON:
      case TRACE_TYPE_INCOMING_EVENT_DROPPED_TOO_LATE:
      case TRACE_TYPE_OUTGOING_COMMAND_ACCEPTED:
      case TRACE_TYPE_OUTGOING_COMMAND_DROPPED_STRUCTURALLY:
      case TRACE_TYPE_OUTGOING_COMMAND_DROPPED_TOO_SOON:
      case TRACE_TYPE_OUTGOING_COMMAND_DROPPED_TOO_LATE:
      case TRACE_TYPE_OUTGOING_COMMAND_QUEUED:
      case TRACE_TYPE_OUTGOING_COMMAND_STARTED:
      case TRACE_TYPE_OUTGOING_COMMAND_FINISHED:
      case TRACE_TYPE_COMMAND_NOT_CHOSEN_TOO_LATE:
        printf("%lu\t%u", trace.data.event.tick, trace.data.event.idx);
        break;
      default:
        configASSERT(false);
    }

    printf("\n");
  }
}

static inline void TraceTickRate()
{
  struct Trace trace = {
    .traceTick = GetTraceTick(),
    .traceType = TRACE_TYPE_TICK_RATE 
  };
  configASSERT(pdPASS == xQueueSendToBack(TraceQueue, &trace, portMAX_DELAY));
}

static inline void TraceNetStartTick(TickType_t startTick)
{
  struct Trace trace = {
    .traceTick = GetTraceTick(),
    .traceType = TRACE_TYPE_NET_START_TICK,
    .data.startTick = startTick
  };
  configASSERT(pdPASS == xQueueSendToBack(TraceQueue, &trace, portMAX_DELAY));
}

static inline void TraceNetUpdate(EventIdx_t eventIdx, TickType_t eventTick, bool isCommand, enum EventStatus eventStatus)
{
  const TraceTickType_t traceTick = GetTraceTick();
  TraceType_t traceType;

  if (isCommand)
  {
    switch (eventStatus)
    {
      case EVENT_STATUS_ENABLED:
        traceType = TRACE_TYPE_OUTGOING_COMMAND_ACCEPTED;
        break;
      case EVENT_STATUS_DISABLED_STRUCTURALLY:
        traceType = TRACE_TYPE_OUTGOING_COMMAND_DROPPED_STRUCTURALLY;
        break;
      case EVENT_STATUS_DISABLED_TOO_SOON:
        traceType = TRACE_TYPE_OUTGOING_COMMAND_DROPPED_TOO_SOON;
        break;
      case EVENT_STATUS_DISABLED_TOO_LATE:
        traceType = TRACE_TYPE_OUTGOING_COMMAND_DROPPED_TOO_LATE;
        break;
      default:
        configASSERT(false);
    }
  }
  else
  {
    switch (eventStatus)
    {
      case EVENT_STATUS_ENABLED:
        traceType = TRACE_TYPE_INCOMING_EVENT_ACCEPTED;
        break;
      case EVENT_STATUS_DISABLED_STRUCTURALLY:
        traceType = TRACE_TYPE_INCOMING_EVENT_DROPPED_STRUCTURALLY;
        break;
      case EVENT_STATUS_DISABLED_TOO_SOON:
        traceType = TRACE_TYPE_INCOMING_EVENT_DROPPED_TOO_SOON;
        break;
      case EVENT_STATUS_DISABLED_TOO_LATE:
        traceType = TRACE_TYPE_INCOMING_EVENT_DROPPED_TOO_LATE;
        break;
      default:
        configASSERT(false);
    }
  }

  const struct Trace trace = {
    .traceTick = traceTick,
    .traceType = traceType,
    .data.event.idx = eventIdx,
    .data.event.tick = eventTick
  };

  configASSERT(pdPASS == xQueueSendToBack(TraceQueue, &trace, portMAX_DELAY));
}

static inline void TraceOutgoingCommandQueued(CommandIdx_t commandIdx, TickType_t eventTick)
{
  struct Trace trace = {
    .traceTick = GetTraceTick(),
    .traceType = TRACE_TYPE_OUTGOING_COMMAND_QUEUED,
    .data.event.idx = CORE_COMMANDS[commandIdx].eventIdx,
    .data.event.tick = eventTick
  };
  configASSERT(pdPASS == xQueueSendToBack(TraceQueue, &trace, portMAX_DELAY));
}

static inline void TraceOutgoingCommandStarted(CommandIdx_t commandIdx, TickType_t eventTick)
{
  struct Trace trace = {
    .traceTick = GetTraceTick(),
    .traceType = TRACE_TYPE_OUTGOING_COMMAND_STARTED,
    .data.event.idx = CORE_COMMANDS[commandIdx].eventIdx,
    .data.event.tick = eventTick
  };
  configASSERT(pdPASS == xQueueSendToBack(TraceQueue, &trace, portMAX_DELAY));
}

static inline void TraceOutgoingCommandFinished(CommandIdx_t commandIdx, TickType_t eventTick)
{
  struct Trace trace = {
    .traceTick = GetTraceTick(),
    .traceType = TRACE_TYPE_OUTGOING_COMMAND_FINISHED,
    .data.event.idx = CORE_COMMANDS[commandIdx].eventIdx,
    .data.event.tick = eventTick
  };
  configASSERT(pdPASS == xQueueSendToBack(TraceQueue, &trace, portMAX_DELAY));
}

static inline void TraceCommandNotChosenTooLate(CommandIdx_t commandIdx, TickType_t eventTick)
{
  struct Trace trace = {
    .traceTick = GetTraceTick(),
    .traceType = TRACE_TYPE_COMMAND_NOT_CHOSEN_TOO_LATE,
    .data.event.idx = CORE_COMMANDS[commandIdx].eventIdx,
    .data.event.tick = eventTick
  };
  configASSERT(pdPASS == xQueueSendToBack(TraceQueue, &trace, portMAX_DELAY));
}

#else

#define TraceTickRate(...) ((void)0)
#define TraceNetStartTick(...) ((void)0)
#define TraceNetUpdate(...) ((void)0)
#define TraceOutgoingCommandQueued(...) ((void)0)
#define TraceOutgoingCommandStarted(...) ((void)0)
#define TraceOutgoingCommandFinished(...) ((void)0)
#define TraceCommandNotChosenTooLate(...) ((void)0)

#endif


/** Petri Net variables and update functions. **/

struct Place corePlaces[CORE_PLACE_COUNT] = { {0}, {1}, {0}, {1}, {0}, {0}, {0}, {1}, {0}, {1}, {0}, {1}, {0} };
TickType_t transitionEnabledTime[CORE_EVENT_COUNT] = { 0 };

enum EventStatus NetGetEventStatus(EventIdx_t eventIdx, TickType_t tick)
{
  if (transitionEnabledTime[eventIdx] == portMAX_DELAY)
    return EVENT_STATUS_DISABLED_STRUCTURALLY;

  const TickType_t timeElapsed = tick - transitionEnabledTime[eventIdx];
  if (timeElapsed < CORE_EVENT_TRANSITIONS[eventIdx].intervalLowerLimit)
    return EVENT_STATUS_DISABLED_TOO_SOON;
  if (CORE_EVENT_TRANSITIONS[eventIdx].intervalUpperLimit != portMAX_DELAY
    && CORE_EVENT_TRANSITIONS[eventIdx].intervalUpperLimit < timeElapsed)
    return EVENT_STATUS_DISABLED_TOO_LATE;

  return EVENT_STATUS_ENABLED;
}

void NetUpdateTransitionEnabledTime(EventIdx_t eventIdx, TickType_t tick)
{
  for (int8_t idx = 0; idx < CORE_EVENT_TRANSITIONS[eventIdx].inhibitorArcsCount; ++idx)
  {
    const PlaceIdx_t arcPlace = CORE_EVENT_TRANSITIONS[eventIdx].inhibitorArcs[idx].placeIdx;
    const ArcWeight_t arcWeight = CORE_EVENT_TRANSITIONS[eventIdx].inhibitorArcs[idx].weight;
    if (corePlaces[arcPlace].markings >= arcWeight)
    {
      transitionEnabledTime[eventIdx] = portMAX_DELAY;
      return;
    }
  }

  for (int8_t idx = 0; idx < CORE_EVENT_TRANSITIONS[eventIdx].inputArcsCount; ++idx)
  {
    const PlaceIdx_t arcPlace = CORE_EVENT_TRANSITIONS[eventIdx].inputArcs[idx].placeIdx;
    const ArcWeight_t arcWeight = CORE_EVENT_TRANSITIONS[eventIdx].inputArcs[idx].weight;
    if (arcWeight > corePlaces[arcPlace].markings)
    {
      transitionEnabledTime[eventIdx] = portMAX_DELAY;
      return;
    }
  }

  if (transitionEnabledTime[eventIdx] == portMAX_DELAY)
    transitionEnabledTime[eventIdx] = tick;
}

enum EventStatus NetTryUpdate(EventIdx_t eventIdx, TickType_t tick)
{
  const enum EventStatus eventStatus = NetGetEventStatus(eventIdx, tick);
  if (eventStatus != EVENT_STATUS_ENABLED)
    return eventStatus;

  for (int8_t idx = 0; idx < CORE_EVENT_TRANSITIONS[eventIdx].deltaArcsCount; ++idx)
  {
    const PlaceIdx_t placeIdx = CORE_EVENT_TRANSITIONS[eventIdx].deltaArcs[idx].placeIdx;
    const ArcWeight_t weight = CORE_EVENT_TRANSITIONS[eventIdx].deltaArcs[idx].weight;
    corePlaces[placeIdx].markings += weight;
  }

  for (int8_t idx = 0; idx < CORE_EVENT_TRANSITIONS[eventIdx].affectedTransitionsCount; ++idx)
    NetUpdateTransitionEnabledTime(CORE_EVENT_TRANSITIONS[eventIdx].affectedTransitions[idx], tick);

  return EVENT_STATUS_ENABLED;
}

bool NetGetNextEnabledCommand(TickType_t currentTick, struct RichCommand *command)
{
  command->tick = portMAX_DELAY;

  for (CommandIdx_t commandIdx = 0; commandIdx < CORE_COMMAND_COUNT; ++commandIdx)
  {
    const EventIdx_t eventIdx = CORE_COMMANDS[commandIdx].eventIdx;

    if (transitionEnabledTime[eventIdx] == portMAX_DELAY)
      continue;

    if (CORE_EVENT_TRANSITIONS[eventIdx].intervalUpperLimit != portMAX_DELAY
      && currentTick > transitionEnabledTime[eventIdx] + CORE_EVENT_TRANSITIONS[eventIdx].intervalUpperLimit)
    {
      TraceCommandNotChosenTooLate(commandIdx, currentTick);
      continue;
    }

    const TickType_t commandEnabledTick = transitionEnabledTime[eventIdx] + CORE_EVENT_TRANSITIONS[eventIdx].intervalLowerLimit;
    if (command->tick == portMAX_DELAY || commandEnabledTick < command->tick)
    {
      command->idx = commandIdx;
      command->tick = commandEnabledTick;
    }
  }

  return command->tick != portMAX_DELAY;
}


/** Core variables, tasks and helper functions. **/

TaskHandle_t TaskEventLoopHandle;
TimerHandle_t TimerScheduleCommandHandle;

void TaskEventLoop(void*)
{
  {
    TraceTickRate();

    // Initialize Petri Net.
    TickType_t startTick = xTaskGetTickCount();
    TraceNetStartTick(startTick);
    for (EventIdx_t eventIdx = 0; eventIdx < CORE_EVENT_COUNT; ++eventIdx)
      NetUpdateTransitionEnabledTime(eventIdx, startTick);

    // Set priority for timer task (TimerScheduleCommand).
    vTaskPrioritySet(xTimerGetTimerDaemonTaskHandle(), CORE_SCHEDULE_COMMAND_TASK_PRIORITY);
  }

  for (;;)
  {
    // Process queued events and execute commands until there are no new events and no immediate commands.
    for (;;)
    {
      // Process all queued events.
      {
        struct RichEvent event;
        while (pdPASS == xQueueReceive(EventQueue, &event, 0))
        {
          if (event.idx == EVENT_SCHEDULED_COMMAND)
            continue;

          const enum EventStatus eventStatus = NetTryUpdate(event.idx, event.tick);
          TraceNetUpdate(event.idx, event.tick, false, eventStatus);
        }
      }

      // Get next enabled command or break if there isn't one.
      struct RichCommand command;
      if (!NetGetNextEnabledCommand(xTaskGetTickCount(), &command))
        break;

      // Return to event processing if a new event arrived while choosing command.
      {
        struct RichEvent event;
        if (pdPASS == xQueuePeek(EventQueue, &event, 0))
          continue;
      }

      const TickType_t currentTick = xTaskGetTickCount();
      if (command.tick > currentTick)
      {
        // Command isn't enabled yet: schedule execution.
        const TickType_t period = command.tick - currentTick;
        configASSERT(pdPASS == xTimerChangePeriod(TimerScheduleCommandHandle, period, portMAX_DELAY));
        configASSERT(pdPASS == xTimerStart(TimerScheduleCommandHandle, portMAX_DELAY));
        TraceOutgoingCommandQueued(command.idx, command.tick);
        break;
      }
      else
      {
        // Command is already enabled: execute immediately.
        const enum EventStatus eventStatus = NetTryUpdate(CORE_COMMANDS[command.idx].eventIdx, currentTick);
        TraceNetUpdate(CORE_COMMANDS[command.idx].eventIdx, currentTick, true, eventStatus);
        if (eventStatus == EVENT_STATUS_ENABLED)
        {
          TraceOutgoingCommandStarted(command.idx, command.tick);
          CORE_COMMANDS[command.idx].handler();
          TraceOutgoingCommandFinished(command.idx, command.tick);
        }
      }
    }

    // Wait for an incoming event.
    {
      struct RichEvent event;
      configASSERT(pdPASS == xQueuePeek(EventQueue, &event, portMAX_DELAY));
    }

    // Cancel pending command timer, if any.
    configASSERT(pdPASS == xTimerStop(TimerScheduleCommandHandle, portMAX_DELAY));
  }
}

void TimerScheduleCommand(TimerHandle_t timerHandle)
{
  if (timerHandle != TimerScheduleCommandHandle)
    // Prevent execution by user code.
    return;

  struct RichEvent scheduledCommand = { .idx = EVENT_SCHEDULED_COMMAND };
  configASSERT(pdPASS == xQueueSendToBack(EventQueue, &scheduledCommand, 0));
}


/** Initialization function. Called by user code. **/

void DesControllerSetup(void)
{
  /* Core initialization. */
  configASSERT(NULL != (EventQueue = xQueueCreate(CORE_EVENT_QUEUE_SIZE, sizeof(struct RichEvent))));

  configASSERT(pdPASS == xTaskCreate(TaskEventLoop, CORE_EVENT_LOOP_TASK_NAME, CORE_EVENT_LOOP_TASK_SDEPTH, NULL, CORE_EVENT_LOOP_TASK_PRIORITY, &TaskEventLoopHandle));
  configASSERT(NULL != (TimerScheduleCommandHandle = xTimerCreate(CORE_SCHEDULE_COMMAND_TASK_NAME, portMAX_DELAY, pdFALSE, NULL, TimerScheduleCommand)));

#ifdef CORE_ENABLE_TRACE
  configASSERT(NULL != (TraceQueue = xQueueCreate(CORE_TRACE_QUEUE_SIZE, sizeof(struct Trace))));
  configASSERT(pdPASS == xTaskCreate(TaskTraceLoop, CORE_TRACE_LOOP_TASK_NAME, CORE_TRACE_LOOP_TASK_SDEPTH, NULL, CORE_TRACE_LOOP_TASK_PRIORITY, &TaskTraceLoopHandle));
#endif

  /* Module initialization. */

}
