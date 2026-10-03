from backend.app.core.hardware_config import load_hardware_config


def test_hardware_config_defaults_unknown_values_to_none():
    config = load_hardware_config({})

    assert config.emg_adc_pin is None
    assert config.ir_sensor_pin is None
    assert config.device_id == "BLINK001"
    assert config.emg_sample_rate is None
    assert config.emg_threshold is None
    assert config.ir_threshold is None
    assert config.supported_sensor_mode == "dual"


def test_hardware_config_reads_configured_values():
    config = load_hardware_config(
        {
            "EMG_ADC_PIN": "4",
            "IR_SENSOR_PIN": "5",
            "DEVICE_ID": "unit-test",
            "EMG_SAMPLE_RATE": "250",
            "EMG_THRESHOLD": "0.75",
            "IR_THRESHOLD": "0.4",
            "SUPPORTED_SENSOR_MODE": "dual",
        }
    )

    assert config.emg_adc_pin == 4
    assert config.ir_sensor_pin == 5
    assert config.device_id == "unit-test"
    assert config.emg_sample_rate == 250
    assert config.emg_threshold == 0.75
    assert config.ir_threshold == 0.4