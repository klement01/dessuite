/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32f1xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define LED_BUILTIN_Pin GPIO_PIN_13
#define LED_BUILTIN_GPIO_Port GPIOC
#define LED_WHITE_1_Pin GPIO_PIN_4
#define LED_WHITE_1_GPIO_Port GPIOA
#define BUTTON_1_Pin GPIO_PIN_5
#define BUTTON_1_GPIO_Port GPIOA
#define LED_WHITE_2_Pin GPIO_PIN_6
#define LED_WHITE_2_GPIO_Port GPIOA
#define BUTTON_2_Pin GPIO_PIN_7
#define BUTTON_2_GPIO_Port GPIOA
#define LED_GREEN_2_Pin GPIO_PIN_3
#define LED_GREEN_2_GPIO_Port GPIOB
#define LED_RED_2_Pin GPIO_PIN_4
#define LED_RED_2_GPIO_Port GPIOB
#define LED_GREEN_1_Pin GPIO_PIN_5
#define LED_GREEN_1_GPIO_Port GPIOB
#define LED_RED_1_Pin GPIO_PIN_6
#define LED_RED_1_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
