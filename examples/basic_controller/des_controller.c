#include "des_controller.h"

#define CORE_ENABLE_TRACE

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef CORE_ENABLE_TRACE
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#endif /* CORE_ENABLE_TRACE */

#include "FreeRTOS.h"
#include "FreeRTOSConfig.h"
#include "portmacro.h"
#include "projdefs.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"
#include "timers.h"

/** Module includes and defines. **/

/* START MODULE HAL GPIO INCLUDES */
/* END MODULE HAL GPIO INCLUDES */
/* START MODULE HAL UART INCLUDES */
/* END MODULE HAL UART INCLUDES */


/** Core data (defines, types and constants). **/

/* User parameters. */

#define CORE_EVENT_QUEUE_SIZE (8)

#define CORE_EVENT_LOOP_TASK_NAME ("DessuiteEventLoop")
#define CORE_EVENT_LOOP_TASK_SDEPTH (configMINIMAL_STACK_SIZE)
#define CORE_EVENT_LOOP_TASK_PRIORITY (configMAX_PRIORITIES - 1)

#define CORE_SCHEDULE_COMMAND_TASK_NAME ("DessuiteScheduleCommand")
#define CORE_SCHEDULE_COMMAND_TASK_PRIORITY (configMAX_PRIORITIES - 2)

#ifdef CORE_ENABLE_TRACE
#define CORE_TRACE_QUEUE_SIZE (16)

#define CORE_TRACE_LOOP_TASK_NAME ("DessuiteTraceLoop")
#define CORE_TRACE_LOOP_TASK_SDEPTH (configMINIMAL_STACK_SIZE)
#define CORE_TRACE_LOOP_TASK_PRIORITY (1)
#endif /* CORE_ENABLE_TRACE */

/* Petri Net definition. */

#define CORE_EVENT_COUNT (2)
#define CORE_COMMAND_COUNT (1)
#define CORE_PLACE_COUNT (2)

typedef uint8_t EventIdx_t;
typedef uint8_t PlaceIdx_t;
typedef uint8_t CommandIdx_t;
typedef uint8_t PlaceMarking_t;
typedef int8_t ArcWeight_t;

enum EventIdx : EventIdx_t
{
  EVENT_0, // T1
  EVENT_1, // T2
  EVENT_SCHEDULED_COMMAND
};

struct TimeStampedEvent
{
  EventIdx_t idx;
  TickType_t tick;
};

struct TimeStampedCommand
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

const struct TransitionArc EVENT_0_INHIBITOR_ARCS[1] = {
  {1, 1}
};
const struct TransitionArc EVENT_0_INPUT_ARCS[1] = {
  {0, 1}
};
const struct TransitionArc EVENT_0_DELTA_ARCS[2] = {
  {0, -1},
  {1, 1}
};
const EventIdx_t EVENT_0_AFFECTED_TRANSITIONS[2] = {0, 1};

const struct TransitionArc EVENT_1_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_1_INPUT_ARCS[2] = {
  {0, 1},
  {1, 1}
};
const struct TransitionArc EVENT_1_DELTA_ARCS[1] = {
  {1, -1}
};
const EventIdx_t EVENT_1_AFFECTED_TRANSITIONS[2] = {0, 1};

const struct EventTransition CORE_EVENT_TRANSITIONS[CORE_EVENT_COUNT] =
{
  {1, 1, 2, 2, EVENT_0_INHIBITOR_ARCS, EVENT_0_INPUT_ARCS, EVENT_0_DELTA_ARCS, EVENT_0_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U)+1, pdMS_TO_TICKS(10U)-1},
  {0, 2, 1, 2, EVENT_1_INHIBITOR_ARCS, EVENT_1_INPUT_ARCS, EVENT_1_DELTA_ARCS, EVENT_1_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(50U)+1, portMAX_DELAY},
};


/** Module variables. **/

/* START MODULE HAL GPIO VARIABLES */
/* END MODULE HAL GPIO VARIABLES */
/* START MODULE HAL UART VARIABLES */
extern UART_HandleTypeDef huart1;
uint8_t huart1_recv_buffer;
uint8_t huart1_transmit_buffer;
/* END MODULE HAL UART VARIABLES */


/** Core command handler. */

struct Command
{
  const enum EventIdx eventIdx;
  const void (*handler)(void);
};

void EVENT_0_COMMAND_HANDLER(void)
{
  /* START MODULE HAL GPIO ACTIONS */
  HAL_GPIO_WritePin(LED_GPIO_Port, LED_Pin, GPIO_PIN_SET);
  /* END MODULE HAL GPIO ACTIONS */
  /* START MODULE HAL UART ACTIONS */
  huart1_transmit_buffer = 10;
  HAL_UART_Transmit_IT(&huart1, &huart1_transmit_buffer, sizeof(huart1_transmit_buffer));;
  /* END MODULE HAL UART ACTIONS */
}

const struct Command CORE_COMMANDS[CORE_COMMAND_COUNT] =
{
  {0, EVENT_0_COMMAND_HANDLER}
};


/** Log functions. **/

typedef uint32_t TaskNumber_t;

#ifdef CORE_ENABLE_TRACE

typedef uint8_t TraceType_t;
typedef uint8_t TraceQueueIdx_t;

enum TaskNumber : TaskNumber_t
{
  TASK_NUMBER_EVENT_LOOP = (1),
  TASK_NUMBER_TIMER      = (2),
  TASK_NUMBER_TRACE_LOOP = (3)
};

enum TraceType : TraceType_t
{
  TRACE_TYPE_TICK_RATE                             = (1),
  TRACE_TYPE_NET_START_TICK                        = (2),
  TRACE_TYPE_INCOMING_EVENT_RECEIVED               = (3),
  TRACE_TYPE_INCOMING_EVENT_ACCEPTED               = (4),
  TRACE_TYPE_INCOMING_EVENT_DROPPED_STRUCTURALLY   = (5),
  TRACE_TYPE_INCOMING_EVENT_DROPPED_TOO_SOON       = (6),
  TRACE_TYPE_INCOMING_EVENT_DROPPED_TOO_LATE       = (7),
  TRACE_TYPE_OUTGOING_COMMAND_ACCEPTED             = (8),
  TRACE_TYPE_OUTGOING_COMMAND_DROPPED_STRUCTURALLY = (9),
  TRACE_TYPE_OUTGOING_COMMAND_DROPPED_TOO_SOON     = (10),
  TRACE_TYPE_OUTGOING_COMMAND_DROPPED_TOO_LATE     = (11),
  TRACE_TYPE_OUTGOING_COMMAND_QUEUED               = (13),
  TRACE_TYPE_OUTGOING_COMMAND_STARTED              = (14),
  TRACE_TYPE_OUTGOING_COMMAND_FINISHED             = (15),
  TRACE_TYPE_COMMAND_NOT_CHOSEN_TOO_LATE           = (16),
  TRACE_TYPE_TASK_SWITCHED_IN                      = (17),
  TRACE_TYPE_TASK_SWITCHED_OUT                     = (18),
  TRACE_TYPE_INTERRUPT_START                       = (19),
  TRACE_TYPE_INTERRUPT_END                         = (20),
};

struct Trace 
{
  TraceTickType_t traceTick;
  TraceType_t traceType;
  union {
    struct TimeStampedEvent event;
    TickType_t startTick;
    TaskNumber_t taskNumber;
  } data;
};

struct
{
  // https://github.com/QuantumLeaps/lock-free-ring-buffer
  struct Trace data[CORE_TRACE_QUEUE_SIZE];
  _Atomic(TraceQueueIdx_t) head;
  _Atomic(TraceQueueIdx_t) tail;
} traceQueue = { 0 };

bool TraceQueuePop(struct Trace **tracePtr)
{
  TraceQueueIdx_t tail = atomic_load_explicit(&traceQueue.tail, memory_order_relaxed);
  const TraceQueueIdx_t head = atomic_load_explicit(&traceQueue.head, memory_order_acquire);
  if (head != tail)
  {
    *tracePtr = &traceQueue.data[tail];
    ++tail;
    if (tail >= CORE_TRACE_QUEUE_SIZE)
      tail = 0U;
    atomic_store_explicit(&traceQueue.tail, tail, memory_order_release);
    return true;
  }
  else
  {
    return false;
  }
}

bool TraceQueuePush(const struct Trace *trace)
{
  TraceQueueIdx_t head = atomic_load_explicit(&traceQueue.head, memory_order_relaxed) + 1U;
  if (head >= CORE_TRACE_QUEUE_SIZE)
    head = 0;

  const TraceQueueIdx_t tail = atomic_load_explicit(&traceQueue.tail, memory_order_acquire);
  if (head != tail)
  {
    memcpy(&traceQueue.data[atomic_load_explicit(&traceQueue.head, memory_order_relaxed)], trace, sizeof(struct Trace));
    atomic_store_explicit(&traceQueue.head, head, memory_order_release);
    return true;
  }
  else
  {
    return false;
  }
}

__weak TraceTickType_t GetTraceTickCount()
{
  return (TraceTickType_t)xTaskGetTickCount();
}

__weak TraceTickType_t GetTraceTickCountFromISR()
{
  return (TraceTickType_t)xTaskGetTickCountFromISR();
}

__weak TraceTickType_t GetTraceTickRate()
{
  return (TraceTickType_t)configTICK_RATE_HZ;
}

TaskHandle_t TaskTraceLoopHandle;

void TaskTraceLoop(void*)
{
  uint32_t traceCount = 0;
  for (;;)
  {
    struct Trace *trace;
    while (TraceQueuePop(&trace))
    {
      printf("%lu\t%lu\t%u", traceCount, trace->traceTick, trace->traceType);
      ++traceCount;

      switch (trace->traceType)
      {
        case TRACE_TYPE_TICK_RATE:
          printf("\t%lu\t%lu", (TraceTickType_t)configTICK_RATE_HZ, GetTraceTickRate());
          break;
        case TRACE_TYPE_NET_START_TICK:
          printf("\t%lu",  trace->data.startTick);
          break;
        case TRACE_TYPE_INCOMING_EVENT_RECEIVED:
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
          printf("\t%lu\t%u", trace->data.event.tick, trace->data.event.idx);
          break;
        case TRACE_TYPE_TASK_SWITCHED_IN:
        case TRACE_TYPE_TASK_SWITCHED_OUT:
          printf("\t%lu",  trace->data.taskNumber);
          break;
        case TRACE_TYPE_INTERRUPT_START:
        case TRACE_TYPE_INTERRUPT_END:
          break;
        default:
          configASSERT(false);
      }

      printf("\n");
    }
  }
}

static inline void TraceTickRate()
{
  struct Trace trace = {
    .traceTick = GetTraceTickCount(),
    .traceType = TRACE_TYPE_TICK_RATE 
  };
  configASSERT(TraceQueuePush(&trace));
}

static inline void TraceNetStartTick(TickType_t startTick)
{
  struct Trace trace = {
    .traceTick = GetTraceTickCount(),
    .traceType = TRACE_TYPE_NET_START_TICK,
    .data.startTick = startTick
  };
  configASSERT(TraceQueuePush(&trace));
}

static inline void TraceIncomingEventReceivedFromISR(EventIdx_t eventIdx, TickType_t eventTick)
{
  struct Trace trace = {
    .traceTick = GetTraceTickCountFromISR(),
    .traceType = TRACE_TYPE_INCOMING_EVENT_RECEIVED,
    .data.event.idx = eventIdx,
    .data.event.tick = eventTick
  };
  configASSERT(TraceQueuePush(&trace));
}

void TraceNetUpdate(EventIdx_t eventIdx, TickType_t eventTick, bool isCommand, enum EventStatus eventStatus)
{
  const TraceTickType_t traceTick = GetTraceTickCount();
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

  configASSERT(TraceQueuePush(&trace));
}

static inline void TraceOutgoingCommandQueued(CommandIdx_t commandIdx, TickType_t eventTick)
{
  struct Trace trace = {
    .traceTick = GetTraceTickCount(),
    .traceType = TRACE_TYPE_OUTGOING_COMMAND_QUEUED,
    .data.event.idx = CORE_COMMANDS[commandIdx].eventIdx,
    .data.event.tick = eventTick
  };
  configASSERT(TraceQueuePush(&trace));
}

static inline void TraceOutgoingCommandStarted(CommandIdx_t commandIdx, TickType_t eventTick)
{
  struct Trace trace = {
    .traceTick = GetTraceTickCount(),
    .traceType = TRACE_TYPE_OUTGOING_COMMAND_STARTED,
    .data.event.idx = CORE_COMMANDS[commandIdx].eventIdx,
    .data.event.tick = eventTick
  };
  configASSERT(TraceQueuePush(&trace));
}

static inline void TraceOutgoingCommandFinished(CommandIdx_t commandIdx, TickType_t eventTick)
{
  struct Trace trace = {
    .traceTick = GetTraceTickCount(),
    .traceType = TRACE_TYPE_OUTGOING_COMMAND_FINISHED,
    .data.event.idx = CORE_COMMANDS[commandIdx].eventIdx,
    .data.event.tick = eventTick
  };
  configASSERT(TraceQueuePush(&trace));
}

static inline void TraceCommandNotChosenTooLate(CommandIdx_t commandIdx, TickType_t eventTick)
{
  struct Trace trace = {
    .traceTick = GetTraceTickCount(),
    .traceType = TRACE_TYPE_COMMAND_NOT_CHOSEN_TOO_LATE,
    .data.event.idx = CORE_COMMANDS[commandIdx].eventIdx,
    .data.event.tick = eventTick
  };
  configASSERT(TraceQueuePush(&trace));
}

void TraceTaskSwitchedIn(TaskNumber_t taskNumber)
{
  struct Trace trace = {
    .traceTick = GetTraceTickCountFromISR(),
    .traceType = TRACE_TYPE_TASK_SWITCHED_IN,
    .data.taskNumber = taskNumber
  };
  configASSERT(TraceQueuePush(&trace));
}

void TraceTaskSwitchedOut(TaskNumber_t taskNumber)
{
  struct Trace trace = {
    .traceTick = GetTraceTickCountFromISR(),
    .traceType = TRACE_TYPE_TASK_SWITCHED_OUT,
    .data.taskNumber = taskNumber
  };
  configASSERT(TraceQueuePush(&trace));
}

static inline void TraceInterruptStart()
{
  struct Trace trace = {
    .traceTick = GetTraceTickCountFromISR(),
    .traceType = TRACE_TYPE_INTERRUPT_START
  };
  configASSERT(TraceQueuePush(&trace));
}

static inline void TraceInterruptEnd()
{
  struct Trace trace = {
    .traceTick = GetTraceTickCountFromISR(),
    .traceType = TRACE_TYPE_INTERRUPT_END
  };
  configASSERT(TraceQueuePush(&trace));
}

#else

#define TraceTickRate() ((void)0)
#define TraceNetStartTick(a) do { (void)a; } while (0)
#define TraceIncomingEventReceivedFromISR(a, b) do { (void)a; (void)b; } while (0)
#define TraceNetUpdate(a, b, c, d) do { (void)a; (void)b; (void)c; (void)d; } while (0)
#define TraceOutgoingCommandQueued(a, b) do { (void)a; (void)b; } while (0)
#define TraceOutgoingCommandStarted(a, b) do { (void)a; (void)b; } while (0)
#define TraceOutgoingCommandFinished(a, b) do { (void)a; (void)b; } while (0)
#define TraceCommandNotChosenTooLate(a, b) do { (void)a; (void)b; } while (0)
void TraceTaskSwitchedIn(TaskNumber_t) {};
void TraceTaskSwitchedOut(TaskNumber_t) {};
#define TraceInterruptStart() ((void)0)
#define TraceInterruptEnd() ((void)0)

#endif /* CORE_ENABLE_TRACE */


/** Event queue, available to module input functions. **/

QueueHandle_t EventQueue;

static inline void QueueNewIncomingEventFromISR(EventIdx_t eventIdx, TickType_t tick, BaseType_t *xHigherPriorityTaskWoken)
{
  TraceIncomingEventReceivedFromISR(eventIdx, tick);
  struct TimeStampedEvent incomingEvent = { .idx = eventIdx, .tick = tick };
  configASSERT(pdPASS == xQueueSendToBackFromISR(EventQueue, &incomingEvent, xHigherPriorityTaskWoken));
}


/** Module input interface functions. **/

/* START MODULE HAL GPIO INPUT INTERFACE FUNCTIONS */
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
  TraceInterruptStart();
  const TickType_t tick = xTaskGetTickCountFromISR();
  BaseType_t xHigherPriorityTaskWoken = pdFALSE;
  switch (GPIO_Pin)
  {
    case BUTTON_Pin:
      QueueNewIncomingEventFromISR(EVENT_1, tick, &xHigherPriorityTaskWoken);
      break;
  }
  TraceInterruptEnd();
  portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}
/* END MODULE HAL GPIO INPUT INTERFACE FUNCTIONS */
/* START MODULE HAL UART INPUT INTERFACE FUNCTIONS */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  TraceInterruptStart();
  const TickType_t tick = xTaskGetTickCountFromISR();
  BaseType_t xHigherPriorityTaskWoken = pdFALSE;
  configASSERT(huart == &huart1);
  switch (huart1_recv_buffer)
  {
    case 20:
      QueueNewIncomingEventFromISR(EVENT_1, tick, &xHigherPriorityTaskWoken);
      break;
  }
  HAL_UART_Receive_IT(&huart1, &huart1_recv_buffer, sizeof(huart1_recv_buffer));
  TraceInterruptEnd();
  portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}
/* END MODULE HAL UART INPUT INTERFACE FUNCTIONS */


/** Petri Net variables and update functions. **/

struct Place corePlaces[CORE_PLACE_COUNT] = { {3}, {0} };
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

bool NetGetNextEnabledCommand(TickType_t currentTick, struct TimeStampedCommand *command)
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
TimerHandle_t TimerScheduledCommandHandle;

void TaskEventLoop(void*)
{
  {
    TraceTickRate();

    // Initialize Petri Net.
    TickType_t startTick = xTaskGetTickCount();
    TraceNetStartTick(startTick);
    for (EventIdx_t eventIdx = 0; eventIdx < CORE_EVENT_COUNT; ++eventIdx)
      NetUpdateTransitionEnabledTime(eventIdx, startTick);

    // Set priority for timer task (TimerScheduledCommand).
    vTaskPrioritySet(xTimerGetTimerDaemonTaskHandle(), CORE_SCHEDULE_COMMAND_TASK_PRIORITY);
#ifdef CORE_ENABLE_TRACE
    vTaskSetTaskNumber(xTimerGetTimerDaemonTaskHandle(), TASK_NUMBER_TIMER);
#endif /* CORE_ENABLE_TRACE */
  }

  for (;;)
  {
    // Process queued events and execute commands until there are no new events and no immediate commands.
    for (;;)
    {
      // Process all queued events.
      {
        struct TimeStampedEvent event;
        while (pdPASS == xQueueReceive(EventQueue, &event, 0))
        {
          if (event.idx == EVENT_SCHEDULED_COMMAND)
            continue;

          const enum EventStatus eventStatus = NetTryUpdate(event.idx, event.tick);
          TraceNetUpdate(event.idx, event.tick, false, eventStatus);
        }
      }

      // Get next enabled command or break if there isn't one.
      struct TimeStampedCommand command;
      if (!NetGetNextEnabledCommand(xTaskGetTickCount(), &command))
        break;

      // Return to event processing if a new event arrived while choosing command.
      {
        struct TimeStampedEvent event;
        if (pdPASS == xQueuePeek(EventQueue, &event, 0))
          continue;
      }

      const TickType_t currentTick = xTaskGetTickCount();
      if (command.tick > currentTick)
      {
        // Command isn't enabled yet: schedule execution.
        const TickType_t period = command.tick - currentTick;
        configASSERT(pdPASS == xTimerChangePeriod(TimerScheduledCommandHandle, period, portMAX_DELAY));
        configASSERT(pdPASS == xTimerStart(TimerScheduledCommandHandle, portMAX_DELAY));
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
      struct TimeStampedEvent event;
      configASSERT(pdPASS == xQueuePeek(EventQueue, &event, portMAX_DELAY));
    }

    // Cancel pending command timer, if any.
    configASSERT(pdPASS == xTimerStop(TimerScheduledCommandHandle, portMAX_DELAY));
  }
}

void TimerScheduledCommand(TimerHandle_t timerHandle)
{
  if (timerHandle != TimerScheduledCommandHandle)
    // Prevent execution by user code.
    return;

  struct TimeStampedEvent scheduledCommand = { .idx = EVENT_SCHEDULED_COMMAND };
  configASSERT(pdPASS == xQueueSendToBack(EventQueue, &scheduledCommand, 0));
}


/** Initialization function. Called by user code. **/

void DesControllerSetup(void)
{
  /* Core initialization. */
  configASSERT(NULL != (EventQueue = xQueueCreate(CORE_EVENT_QUEUE_SIZE, sizeof(struct TimeStampedEvent))));

  configASSERT(pdPASS == xTaskCreate(TaskEventLoop, CORE_EVENT_LOOP_TASK_NAME, CORE_EVENT_LOOP_TASK_SDEPTH, NULL, CORE_EVENT_LOOP_TASK_PRIORITY, &TaskEventLoopHandle));
  configASSERT(NULL != (TimerScheduledCommandHandle = xTimerCreate(CORE_SCHEDULE_COMMAND_TASK_NAME, portMAX_DELAY, pdFALSE, NULL, TimerScheduledCommand)));

#ifdef CORE_ENABLE_TRACE
  configASSERT(pdPASS == xTaskCreate(TaskTraceLoop, CORE_TRACE_LOOP_TASK_NAME, CORE_TRACE_LOOP_TASK_SDEPTH, NULL, CORE_TRACE_LOOP_TASK_PRIORITY, &TaskTraceLoopHandle));
#endif /* CORE_ENABLE_TRACE */

  /* Module initialization. */
  /* START MODULE HAL GPIO INIT FUNCTION CALLS */
  /* END MODULE HAL GPIO INIT FUNCTION CALLS */
  /* START MODULE HAL UART INIT FUNCTION CALLS */
  HAL_UART_Receive_IT(&huart1, &huart1_recv_buffer, sizeof(huart1_recv_buffer));
  /* END MODULE HAL UART INIT FUNCTION CALLS */

  /* Task metadata. */
#ifdef CORE_ENABLE_TRACE
  vTaskSetTaskNumber(TaskEventLoopHandle, TASK_NUMBER_EVENT_LOOP);
  vTaskSetTaskNumber(TaskTraceLoopHandle, TASK_NUMBER_TRACE_LOOP);
#endif /* CORE_ENABLE_TRACE */
}
