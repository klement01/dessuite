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
#define CORE_EVENT_COUNT (4)
#define CORE_COMMAND_COUNT (2)
#define CORE_PLACE_COUNT (4)

typedef uint8_t EventIdx_t;
typedef uint8_t PlaceIdx_t;
typedef uint8_t CommandIdx_t;
typedef uint8_t PlaceMarking_t;
typedef int8_t ArcWeight_t;

enum EventIdx : EventIdx_t
{
  DISABLE_GREEN_ENABLE_RED,
  ENABLE_GREEN_DISABLE_RED,
  GREEN_BUTTON_PRESSED,
  RED_BUTTON_PRESSED,
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
  const int8_t inputArcsCount;
  const int8_t deltaArcsCount;
  const struct TransitionArc *inputArcs;
  const struct TransitionArc *deltaArcs;
};

const struct TransitionArc EVENT_0_INPUT_ARCS[1] = {
  {1, 1}
};
const struct TransitionArc EVENT_0_DELTA_ARCS[2] = {
  {1, -1},
  {2, 1}
};
const struct TransitionArc EVENT_1_INPUT_ARCS[1] = {
  {3, 1}
};
const struct TransitionArc EVENT_1_DELTA_ARCS[2] = {
  {0, 1},
  {3, -1}
};
const struct TransitionArc EVENT_2_INPUT_ARCS[1] = {
  {2, 1}
};
const struct TransitionArc EVENT_2_DELTA_ARCS[2] = {
  {2, -1},
  {3, 1}
};
const struct TransitionArc EVENT_3_INPUT_ARCS[1] = {
  {0, 1}
};
const struct TransitionArc EVENT_3_DELTA_ARCS[2] = {
  {0, -1},
  {1, 1}
};

const struct EventTransition CORE_EVENT_TRANSITIONS[EVENT_COUNT] =
{
  {1, 2, EVENT_0_INPUT_ARCS, EVENT_0_DELTA_ARCS},
  {1, 2, EVENT_1_INPUT_ARCS, EVENT_1_DELTA_ARCS},
  {1, 2, EVENT_2_INPUT_ARCS, EVENT_2_DELTA_ARCS},
  {1, 2, EVENT_3_INPUT_ARCS, EVENT_3_DELTA_ARCS},
};


/** Core variables. **/

/* Current state. */
struct Place corePlaces[CORE_PLACE_COUNT] = { 0, 0, 0, 1 };

/* Inter-task communication. */
QueueHandle_t PendingEventsQueue;
TaskHandle_t ExecuteCommandTaskHandle;
TaskHandle_t SetCommandTaskHandle;
TaskHandle_t UpdateStateTaskHandle;
TaskHandle_t TraceTaskHandle;


/** Module data (defines, types and constants). **/




/** Module variables. **/




/** Module function definitions. **/




/** Module input interface functions. **/




/** Module output interface functions. **/




/** Core command handler. */

struct Command
{
  const enum EventIdx eventIdx;
  const void (*handler)(void);
};

void COMMAND_0_HANDLER(void)
{
}
void COMMAND_1_HANDLER(void)
{
}

const struct Command CORE_COMMANDS[CORE_COMMAND_COUNT] =
{
  {0, COMMAND_0_HANDLER},
  {1, COMMAND_1_HANDLER}
};


/** Core tasks. **/

bool EventTransitionIsEnabled(EventIdx_t eventIdx)
{
  for (int8_t idx = 0; idx < CORE_EVENT_TRANSITIONS[eventIdx].inputArcsCount; ++idx)
  {
    const PlaceIdx_t arcPlace = CORE_EVENT_TRANSITIONS[eventIdx].inputArcs[idx].placeIdx;
    const ArcWeight_t arcWeight = CORE_EVENT_TRANSITIONS[eventIdx].inputArcs[idx].weight;
    if (arcWeight > corePlaces[arcPlace].markings)
      return false;
  }
  return true;
}

void ExecuteCommand(void*)
{
  for (;;)
  {
    const CommandIdx_t commandIdx = ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    const EventIdx_t eventIdx = CORE_COMMANDS[commandIdx].eventIdx;
    if (xQueueSendToBack(PendingEventsQueue, &eventIdx, 0) != pdPASS)
    CORE_COMMANDS[commandIdx].handler();
  }
}

void UpdateState(void*)
{
  for (;;)
  {
    EventIdx_t event;
    if (xQueueReceive(PendingEventsQueue, &event, portMAX_DELAY) != pdPASS)
      continue;
    if (!EventTransitionIsEnabled(event))
      continue;
    for (int8_t idx = 0; idx < CORE_EVENT_TRANSITIONS[event].deltaArcsCount; ++idx)
    {
      const PlaceIdx_t placeIdx = CORE_EVENT_TRANSITIONS[event].deltaArcs[idx].placeIdx;
      const ArcWeight_t weight = CORE_EVENT_TRANSITIONS[event].deltaArcs[idx].weight;
      corePlaces[placeIdx].markings += weight;
    }
    xTaskNotifyGive(SetCommandTaskHandle);
  }
}

void SetCommand(void*)
{
  for (;;)
  {
    bool commandFound = false;
    CommandIdx_t commandIdx;
    do
    {
      commandFound = false;
      for (commandIdx = 0; commandIdx < COMMAND_COUNT; ++commandIdx)
      {
        if (EventTransitionIsEnabled(CORE_COMMANDS[commandIdx].eventIdx))
        {
          commandFound = true;
          break;
        }
      }
    } while (ulTaskNotifyTake(pdTRUE, 0) != 0);
    if (commandFound)
      xTaskNotify(ExecuteCommandTaskHandle, commandIdx, eSetValueWithOverwrite);
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
  }
}


/** Initialization function. Called by user code. **/

void DesControllerSetup(void)
{
  /* Core initialization. */
  PendingEventsQueue = xQueueCreate(CORE_EVENT_QUEUE_SIZE, sizeof(EventIdx_t));
  xTaskCreate(ExecuteCommand, CORE_EXECUTE_COMMAND_NAME, CORE_EXECUTE_COMMAND_SDEPTH, NULL, CORE_EXECUTE_COMMAND_PRIORITY, &ExecuteCommandTaskHandle);
  xTaskCreate(UpdateState, CORE_UPDATE_STATE_NAME, CORE_UPDATE_STATE_SDEPTH, NULL, CORE_UPDATE_STATE_PRIORITY, &UpdateStateTaskHandle);
  xTaskCreate(SetCommand, CORE_SET_COMMAND_NAME, CORE_SET_COMMAND_SDEPTH, NULL, CORE_SET_COMMAND_PRIORITY, &SetCommandTaskHandle);

  /* Module initialization. */
  
}
