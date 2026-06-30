#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

static const char *TAG = "ALFREDO_MAIN";

void app_main(void)
{
    ESP_LOGI(TAG, "Inicializando Alfredo Satellite (ESP32-S3)...");
    
    // TODO: Inicializar NVS
    // TODO: Inicializar Wi-Fi
    // TODO: Inicializar Display (GC9A01)
    // TODO: Inicializar Audio

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
