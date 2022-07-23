# Thermosmart custom component for HomeAssistant
The `thermosmart` component lets you control a thermostats and view sensor data (boiler information) from [Thermosmart](https://www.thermosmart.com) thermostats. 

<p class='note'>
Boiler information is only available if you have an OpenTherm boiler and if the ot-scope is enabled by Thermosmart for your API-keys.
</p>

## Prerequisites
You will need to obtain a **Client ID** and **Client Secret** from Thermosmart. To obtain this, do the following:

- Fill in the [ThermoSmart API client registration form](https://docs.google.com/forms/d/e/1FAIpQLScraqXO-gfGMM7COfuMugwmgRlYYsTA292TjwuZctgahCilwQ/viewform?c=0&w=1)
- The thermosmart can push changes to a webhook. If you want to use webhooks, fill in the **Webhook URL**:
  
  If you are not using SSL:
  `http://<your_home_assistant_url:<port>/api/webhook/WEBHOOK_ID`

  If you are using SSL:
  `https://<your_home_assistant_url>:<port>/api/webhook/WEBHOOK_ID`
  
## Installation
You can install this component via HACS by adding this resposistory as a [custom respository](https://github.com/theneweinstein/thermosmart_component.git). Alternatively you can manually copy the files into the *thermosmart* folder in the `config` directory.
  
## Configuration
To set it up, go to: https://my.home-assistant.io/redirect/config_flow_start/?domain=thermosmart and follow the instructions.

## Options
If you use a webhook, you can set the Webhook ID in the Configuration options. If you use webhooks, the update function (updates every 5 minutes) will be disabled. To remove the webhook, fill in 'None'.

