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
#include "main.h"

/** Module includes. **/




/** Core data (defines, types and constants). **/

/* User parameters. */
#define CORE_EVENT_QUEUE_SIZE (32)

#define CORE_EXECUTE_COMMAND_NAME ("ExecuteCommand")
#define CORE_UPDATE_STATE_NAME ("UpdateState")
#define CORE_SET_COMMAND_NAME ("SetCommand")

#define CORE_EXECUTE_COMMAND_SDEPTH (configMINIMAL_STACK_SIZE)
#define CORE_UPDATE_STATE_SDEPTH (configMINIMAL_STACK_SIZE)
#define CORE_SET_COMMAND_SDEPTH (configMINIMAL_STACK_SIZE)

#define CORE_EXECUTE_COMMAND_PRIORITY (12)
#define CORE_UPDATE_STATE_PRIORITY (11)
#define CORE_SET_COMMAND_PRIORITY (10)

/* Petri Net definition. */
#define CORE_EVENT_COUNT (13)
#define CORE_COMMAND_COUNT (6)
#define CORE_PLACE_COUNT (11)

typedef uint8_t EventIdx_t;
typedef uint8_t PlaceIdx_t;
typedef uint8_t CommandIdx_t;
typedef uint8_t PlaceMarking_t;
typedef int8_t ArcWeight_t;

enum EventIdx : EventIdx_t
{
  EVENT_0, // cb1_bm+
  EVENT_1, // cb1_boff
  EVENT_2, // cb1_wpar
  EVENT_3, // cb1_wplv
  EVENT_4, // op_l1off
  EVENT_5, // op_l1on
  EVENT_6, // sf1_fdhome
  EVENT_7, // sf1_fdoff
  EVENT_8, // sf1_fdon
  EVENT_9, // sf1_wpar
  EVENT_10, // sf1_wplv
  EVENT_11, // xs1_wpar
  EVENT_12, // xs1_wplv
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
  {10, 1}
};
const struct TransitionArc EVENT_0_INPUT_ARCS[2] = {
  {0, 1},
  {8, 1}
};
const struct TransitionArc EVENT_0_DELTA_ARCS[2] = {
  {0, -1},
  {1, 1}
};
const EventIdx_t EVENT_0_AFFECTED_TRANSITIONS[2] = {0, 1};

const struct TransitionArc EVENT_1_INHIBITOR_ARCS[3] = {
  {2, 1},
  {3, 1},
  {8, 1}
};
const struct TransitionArc EVENT_1_INPUT_ARCS[1] = {
  {1, 1}
};
const struct TransitionArc EVENT_1_DELTA_ARCS[2] = {
  {0, 1},
  {1, -1}
};
const EventIdx_t EVENT_1_AFFECTED_TRANSITIONS[2] = {0, 1};

const struct TransitionArc EVENT_2_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_2_INPUT_ARCS[1] = {
  {8, 1}
};
const struct TransitionArc EVENT_2_DELTA_ARCS[2] = {
  {2, 1},
  {8, -1}
};
const EventIdx_t EVENT_2_AFFECTED_TRANSITIONS[4] = {0, 1, 2, 3};

const struct TransitionArc EVENT_3_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_3_INPUT_ARCS[1] = {
  {2, 1}
};
const struct TransitionArc EVENT_3_DELTA_ARCS[2] = {
  {2, -1},
  {3, 1}
};
const EventIdx_t EVENT_3_AFFECTED_TRANSITIONS[3] = {1, 3, 11};

const struct TransitionArc EVENT_4_INHIBITOR_ARCS[1] = {
  {10, 1}
};
const struct TransitionArc EVENT_4_INPUT_ARCS[1] = {
  {4, 1}
};
const struct TransitionArc EVENT_4_DELTA_ARCS[1] = {
  {4, -1}
};
const EventIdx_t EVENT_4_AFFECTED_TRANSITIONS[2] = {4, 5};

const struct TransitionArc EVENT_5_INHIBITOR_ARCS[1] = {
  {4, 1}
};
const struct TransitionArc EVENT_5_INPUT_ARCS[1] = {
  {10, 1}
};
const struct TransitionArc EVENT_5_DELTA_ARCS[1] = {
  {4, 1}
};
const EventIdx_t EVENT_5_AFFECTED_TRANSITIONS[2] = {4, 5};

const struct TransitionArc EVENT_6_INHIBITOR_ARCS[1] = {
  {9, 1}
};
const struct TransitionArc EVENT_6_INPUT_ARCS[0] = {};
const struct TransitionArc EVENT_6_DELTA_ARCS[1] = {
  {9, 1}
};
const EventIdx_t EVENT_6_AFFECTED_TRANSITIONS[2] = {6, 7};

const struct TransitionArc EVENT_7_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_7_INPUT_ARCS[2] = {
  {6, 1},
  {9, 1}
};
const struct TransitionArc EVENT_7_DELTA_ARCS[3] = {
  {5, 1},
  {6, -1},
  {9, -1}
};
const EventIdx_t EVENT_7_AFFECTED_TRANSITIONS[3] = {6, 7, 8};

const struct TransitionArc EVENT_8_INHIBITOR_ARCS[1] = {
  {10, 1}
};
const struct TransitionArc EVENT_8_INPUT_ARCS[2] = {
  {5, 1},
  {7, 1}
};
const struct TransitionArc EVENT_8_DELTA_ARCS[2] = {
  {5, -1},
  {6, 1}
};
const EventIdx_t EVENT_8_AFFECTED_TRANSITIONS[2] = {7, 8};

const struct TransitionArc EVENT_9_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_9_INPUT_ARCS[0] = {};
const struct TransitionArc EVENT_9_DELTA_ARCS[1] = {
  {7, 1}
};
const EventIdx_t EVENT_9_AFFECTED_TRANSITIONS[2] = {8, 10};

const struct TransitionArc EVENT_10_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_10_INPUT_ARCS[1] = {
  {7, 1}
};
const struct TransitionArc EVENT_10_DELTA_ARCS[2] = {
  {7, -1},
  {8, 1}
};
const EventIdx_t EVENT_10_AFFECTED_TRANSITIONS[5] = {0, 1, 2, 8, 10};

const struct TransitionArc EVENT_11_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_11_INPUT_ARCS[1] = {
  {3, 1}
};
const struct TransitionArc EVENT_11_DELTA_ARCS[2] = {
  {3, -1},
  {10, 1}
};
const EventIdx_t EVENT_11_AFFECTED_TRANSITIONS[7] = {0, 1, 4, 5, 8, 11, 12};

const struct TransitionArc EVENT_12_INHIBITOR_ARCS[0] = {};
const struct TransitionArc EVENT_12_INPUT_ARCS[1] = {
  {10, 1}
};
const struct TransitionArc EVENT_12_DELTA_ARCS[1] = {
  {10, -1}
};
const EventIdx_t EVENT_12_AFFECTED_TRANSITIONS[5] = {0, 4, 5, 8, 12};

const struct EventTransition CORE_EVENT_TRANSITIONS[CORE_EVENT_COUNT] =
{
  {1, 2, 2, 2, EVENT_0_INHIBITOR_ARCS, EVENT_0_INPUT_ARCS, EVENT_0_DELTA_ARCS, EVENT_0_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {3, 1, 2, 2, EVENT_1_INHIBITOR_ARCS, EVENT_1_INPUT_ARCS, EVENT_1_DELTA_ARCS, EVENT_1_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {0, 1, 2, 4, EVENT_2_INHIBITOR_ARCS, EVENT_2_INPUT_ARCS, EVENT_2_DELTA_ARCS, EVENT_2_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {0, 1, 2, 3, EVENT_3_INHIBITOR_ARCS, EVENT_3_INPUT_ARCS, EVENT_3_DELTA_ARCS, EVENT_3_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {1, 1, 1, 2, EVENT_4_INHIBITOR_ARCS, EVENT_4_INPUT_ARCS, EVENT_4_DELTA_ARCS, EVENT_4_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {1, 1, 1, 2, EVENT_5_INHIBITOR_ARCS, EVENT_5_INPUT_ARCS, EVENT_5_DELTA_ARCS, EVENT_5_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(2000U), portMAX_DELAY},
  {1, 0, 1, 2, EVENT_6_INHIBITOR_ARCS, EVENT_6_INPUT_ARCS, EVENT_6_DELTA_ARCS, EVENT_6_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {0, 2, 3, 3, EVENT_7_INHIBITOR_ARCS, EVENT_7_INPUT_ARCS, EVENT_7_DELTA_ARCS, EVENT_7_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {1, 2, 2, 2, EVENT_8_INHIBITOR_ARCS, EVENT_8_INPUT_ARCS, EVENT_8_DELTA_ARCS, EVENT_8_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {0, 0, 1, 2, EVENT_9_INHIBITOR_ARCS, EVENT_9_INPUT_ARCS, EVENT_9_DELTA_ARCS, EVENT_9_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {0, 1, 2, 5, EVENT_10_INHIBITOR_ARCS, EVENT_10_INPUT_ARCS, EVENT_10_DELTA_ARCS, EVENT_10_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {0, 1, 2, 7, EVENT_11_INHIBITOR_ARCS, EVENT_11_INPUT_ARCS, EVENT_11_DELTA_ARCS, EVENT_11_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
  {0, 1, 1, 5, EVENT_12_INHIBITOR_ARCS, EVENT_12_INPUT_ARCS, EVENT_12_DELTA_ARCS, EVENT_12_AFFECTED_TRANSITIONS, pdMS_TO_TICKS(0U), portMAX_DELAY},
};


/** Inter-task communication, available to modules. **/

QueueHandle_t IncomingEventsQueue;

void NewIncomingEventISR(EventIdx_t eventIdx, TickType_t tick, BaseType_t *xHigherPriorityTaskWoken)
{
  struct RichEvent incomingEvent = { .idx = eventIdx, .tick = tick };
  xQueueSendToBackFromISR(IncomingEventsQueue, &incomingEvent, xHigherPriorityTaskWoken);
}

/** Module data (defines, types and constants). **/




/** Module variables. **/

extern UART_HandleTypeDef huart1;
uint8_t huart1_recv_buffer;
uint8_t huart1_transmit_buffer;


/** Module function definitions. **/




/** Module input interface functions. **/

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  const TickType_t tick = xTaskGetTickCountFromISR();
  BaseType_t xHigherPriorityTaskWoken = pdFALSE;
  if (huart != &huart1) portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
  switch (huart1_recv_buffer)
  {
    case 0:
      NewIncomingEventISR(EVENT_6, tick, &xHigherPriorityTaskWoken);
      break;
    case 1:
      NewIncomingEventISR(EVENT_9, tick, &xHigherPriorityTaskWoken);
      break;
    case 2:
      NewIncomingEventISR(EVENT_10, tick, &xHigherPriorityTaskWoken);
      break;
    case 3:
      NewIncomingEventISR(EVENT_2, tick, &xHigherPriorityTaskWoken);
      break;
    case 4:
      NewIncomingEventISR(EVENT_3, tick, &xHigherPriorityTaskWoken);
      break;
    case 5:
      NewIncomingEventISR(EVENT_11, tick, &xHigherPriorityTaskWoken);
      break;
    case 6:
      NewIncomingEventISR(EVENT_12, tick, &xHigherPriorityTaskWoken);
      break;
  }
  HAL_UART_Receive_IT(&huart1, &huart1_recv_buffer, sizeof(huart1_recv_buffer));
  portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}


/** Module output interface functions. **/




/** Core command handler. */

struct Command
{
  const enum EventIdx eventIdx;
  const void (*handler)(void);
};

void EVENT_8_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_GREEN_1_GPIO_Port, LED_GREEN_1_Pin, GPIO_PIN_RESET);
  huart1_transmit_buffer = 7;
  HAL_UART_Transmit_IT(&huart1, &huart1_transmit_buffer, sizeof(huart1_transmit_buffer));;
}
void EVENT_7_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_GREEN_1_GPIO_Port, LED_GREEN_1_Pin, GPIO_PIN_SET);
  huart1_transmit_buffer = 8;
  HAL_UART_Transmit_IT(&huart1, &huart1_transmit_buffer, sizeof(huart1_transmit_buffer));;
}
void EVENT_0_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_GREEN_2_GPIO_Port, LED_GREEN_2_Pin, GPIO_PIN_RESET);
  huart1_transmit_buffer = 9;
  HAL_UART_Transmit_IT(&huart1, &huart1_transmit_buffer, sizeof(huart1_transmit_buffer));;
}
void EVENT_1_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_GREEN_2_GPIO_Port, LED_GREEN_2_Pin, GPIO_PIN_SET);
  huart1_transmit_buffer = 10;
  HAL_UART_Transmit_IT(&huart1, &huart1_transmit_buffer, sizeof(huart1_transmit_buffer));;
}
void EVENT_5_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_RED_1_GPIO_Port, LED_RED_1_Pin, GPIO_PIN_RESET);
  huart1_transmit_buffer = 11;
  HAL_UART_Transmit_IT(&huart1, &huart1_transmit_buffer, sizeof(huart1_transmit_buffer));;
}
void EVENT_4_COMMAND_HANDLER(void)
{
  HAL_GPIO_WritePin(LED_RED_1_GPIO_Port, LED_RED_1_Pin, GPIO_PIN_SET);
  huart1_transmit_buffer = 12;
  HAL_UART_Transmit_IT(&huart1, &huart1_transmit_buffer, sizeof(huart1_transmit_buffer));;
}

const struct Command CORE_COMMANDS[CORE_COMMAND_COUNT] =
{
  {8, EVENT_8_COMMAND_HANDLER},
  {7, EVENT_7_COMMAND_HANDLER},
  {0, EVENT_0_COMMAND_HANDLER},
  {1, EVENT_1_COMMAND_HANDLER},
  {5, EVENT_5_COMMAND_HANDLER},
  {4, EVENT_4_COMMAND_HANDLER}
};


/** Petri Net variables and update functions. **/

struct Place corePlaces[CORE_PLACE_COUNT] = { {1}, {0}, {0}, {0}, {0}, {1}, {0}, {0}, {0}, {0}, {0} };
TickType_t transitionEnabledTime[CORE_EVENT_COUNT] = { 0 };

bool NetIsTransitionStructurallyEnabled(EventIdx_t eventIdx)
{
  for (int8_t idx = 0; idx < CORE_EVENT_TRANSITIONS[eventIdx].inhibitorArcsCount; ++idx)
  {
    const PlaceIdx_t arcPlace = CORE_EVENT_TRANSITIONS[eventIdx].inhibitorArcs[idx].placeIdx;
    const ArcWeight_t arcWeight = CORE_EVENT_TRANSITIONS[eventIdx].inhibitorArcs[idx].weight;
    if (corePlaces[arcPlace].markings >= arcWeight)
      return false;
  }

  for (int8_t idx = 0; idx < CORE_EVENT_TRANSITIONS[eventIdx].inputArcsCount; ++idx)
  {
    const PlaceIdx_t arcPlace = CORE_EVENT_TRANSITIONS[eventIdx].inputArcs[idx].placeIdx;
    const ArcWeight_t arcWeight = CORE_EVENT_TRANSITIONS[eventIdx].inputArcs[idx].weight;
    if (arcWeight > corePlaces[arcPlace].markings)
      return false;
  }

  return true;
}

bool NetIsTransitionEnabled(EventIdx_t eventIdx, TickType_t tick)
{
  if (transitionEnabledTime[eventIdx] == portMAX_DELAY)
    return false;

  const TickType_t timeElapsed = tick - transitionEnabledTime[eventIdx];
  return (CORE_EVENT_TRANSITIONS[eventIdx].intervalLowerLimit <= timeElapsed)
    && (timeElapsed <= CORE_EVENT_TRANSITIONS[eventIdx].intervalUpperLimit);
}

void NetUpdateTransitionEnabledTime(EventIdx_t eventIdx, TickType_t tick)
{
    if (NetIsTransitionStructurallyEnabled(eventIdx))
    {
      if (transitionEnabledTime[eventIdx] == portMAX_DELAY)
        transitionEnabledTime[eventIdx] = tick;
    }
    else
    {
      transitionEnabledTime[eventIdx] = portMAX_DELAY;
    }
}

bool NetTryUpdate(EventIdx_t eventIdx, TickType_t tick)
{
  if (!NetIsTransitionEnabled(eventIdx, tick))
    return false;

  for (int8_t idx = 0; idx < CORE_EVENT_TRANSITIONS[eventIdx].deltaArcsCount; ++idx)
  {
    const PlaceIdx_t placeIdx = CORE_EVENT_TRANSITIONS[eventIdx].deltaArcs[idx].placeIdx;
    const ArcWeight_t weight = CORE_EVENT_TRANSITIONS[eventIdx].deltaArcs[idx].weight;
    corePlaces[placeIdx].markings += weight;
  }

  for (int8_t idx = 0; idx < CORE_EVENT_TRANSITIONS[eventIdx].affectedTransitionsCount; ++idx)
    NetUpdateTransitionEnabledTime(CORE_EVENT_TRANSITIONS[eventIdx].affectedTransitions[idx], tick);

  return true;
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
      continue;

    const TickType_t commandEnabledTick = transitionEnabledTime[eventIdx] + CORE_EVENT_TRANSITIONS[eventIdx].intervalLowerLimit;
    if (command->tick == portMAX_DELAY || commandEnabledTick < command->tick)
    {
      command->idx = commandIdx;
      command->tick = commandEnabledTick;
    }
  }

  return command->tick != portMAX_DELAY;
}


/** Core variables and tasks. **/

SemaphoreHandle_t NetMutex;
TaskHandle_t TaskLoopHandlePetriNetUpdatesHandle;
TaskHandle_t TaskLoopHandleIncomingEventsHandle;
TimerHandle_t TimerOneshotExecuteOutgoingCommandHandle;
CommandIdx_t outgoingCommand; // TODO: fix.

void NetLock()
{
  xSemaphoreTake(NetMutex, portMAX_DELAY);
}

void NetRelease()
{
  xSemaphoreGive(NetMutex);
}

void NetNotifyUpdate()
{
  xTaskNotify(TaskLoopHandlePetriNetUpdatesHandle, 0, eNoAction);
}

void NetWaitForUpdate()
{
  ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
}

void TaskLoopHandlePetriNetUpdates(void*)
{
  {
    // TODO: move elsewhere.
    TickType_t tick = xTaskGetTickCount();
    for (EventIdx_t eventIdx = 0; eventIdx < CORE_EVENT_COUNT; ++eventIdx)
      NetUpdateTransitionEnabledTime(eventIdx, tick);
  }

  for (;;)
  {
    NetLock();
    struct RichCommand nextEnabledCommand;
    const bool foundEnabledCommand = NetGetNextEnabledCommand(xTaskGetTickCount(), &nextEnabledCommand);
    NetRelease();

    if (foundEnabledCommand)
    {
      outgoingCommand = nextEnabledCommand.idx;
      const TickType_t currentTick = xTaskGetTickCount();
      const TickType_t period = nextEnabledCommand.tick > currentTick
        ? nextEnabledCommand.tick - currentTick
        : 1;
      xTimerChangePeriod(TimerOneshotExecuteOutgoingCommandHandle, period, portMAX_DELAY);
      xTimerStart(TimerOneshotExecuteOutgoingCommandHandle, portMAX_DELAY);
    }

    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    xTimerStop(TimerOneshotExecuteOutgoingCommandHandle, portMAX_DELAY);
  }
}

void TaskLoopHandleIncomingEvents(void*)
{
  for (;;)
  {
    struct RichEvent event;
    if (xQueueReceive(IncomingEventsQueue, &event, portMAX_DELAY) != pdPASS)
      continue;

    NetLock();
    const bool netUpdated = NetTryUpdate(event.idx, event.tick);
    NetRelease();

    if (netUpdated)
      NetNotifyUpdate();
  }
}

void TimerOneshotExecuteOutgoingCommand(TimerHandle_t)
{
    const TickType_t tick = xTaskGetTickCount();
    const CommandIdx_t commandIdx = outgoingCommand; // TODO: fix.

    NetLock();
    const bool netUpdated = NetTryUpdate(CORE_COMMANDS[commandIdx].eventIdx, tick);
    NetRelease();

    if (netUpdated)
    {
      NetNotifyUpdate();
      CORE_COMMANDS[commandIdx].handler();
    }
}


/** Initialization function. Called by user code. **/

void DesControllerSetup(void)
{
  /* Core initialization. */
  NetMutex = xSemaphoreCreateMutex();
  IncomingEventsQueue = xQueueCreate(CORE_EVENT_QUEUE_SIZE, sizeof(struct RichEvent));

  // TODO: config? PS Priority = 0 -> idle
  xTaskCreate(TaskLoopHandlePetriNetUpdates, "HandlePetriNetUpdates", configMINIMAL_STACK_SIZE, NULL, 9, &TaskLoopHandlePetriNetUpdatesHandle);
  xTaskCreate(TaskLoopHandleIncomingEvents, "HandleIncomingEvents", configMINIMAL_STACK_SIZE, NULL, 10, &TaskLoopHandleIncomingEventsHandle);
  TimerOneshotExecuteOutgoingCommandHandle = xTimerCreate("ExecuteOutgoingCommand", portMAX_DELAY, pdFALSE, NULL, TimerOneshotExecuteOutgoingCommand);

  /* Module initialization. */
  HAL_UART_Receive_IT(&huart1, &huart1_recv_buffer, sizeof(huart1_recv_buffer));
}
