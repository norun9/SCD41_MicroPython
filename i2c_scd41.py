from machine import I2C, Pin
import time

# Constants
I2C_MASTER_SCL_IO = 21  # SCLピンの番号、必要に応じて調整
I2C_MASTER_SDA_IO = 22  # SDAピンの番号、必要に応じて調整
I2C_MASTER_FREQ_HZ = 400000 # I2Cクロックの周波数 I2C通信速度: 最大400 kHz
SCD41_SENSOR_ADDR = 0x62 # SCD41のI2Cアドレス

# I2C initialization
i2c = I2C(0, scl=Pin(I2C_MASTER_SCL_IO), sda=Pin(I2C_MASTER_SDA_IO), freq=I2C_MASTER_FREQ_HZ)

# CRC8 Polynomial and Initial Value
CRC8_POLYNOMIAL = 0x31
CRC8_INIT = 0xFF

def generate_crc(data):
    crc = CRC8_INIT
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ CRC8_POLYNOMIAL
            else:
                crc <<= 1
            crc &= 0xFF
    return crc

def stop_periodic_measurements():
    i2c.writeto(SCD41_SENSOR_ADDR, bytes([0x3F, 0x86]))

def start_periodic_measurements():
    i2c.writeto(SCD41_SENSOR_ADDR, bytes([0x21, 0xB1]))

def get_data_ready_status():
    i2c.writeto(SCD41_SENSOR_ADDR, bytes([0xE4, 0xB8]))
    read_buf = i2c.readfrom(SCD41_SENSOR_ADDR, 3)
    answer = int.from_bytes(read_buf[:2], 'big')
    return (answer & 0x07FF) != 0

def read_measurement():
    # センサーに0xEC05というコマンドを送信します。このコマンドは、測定データを読み出すためのものです。
    i2c.writeto(SCD41_SENSOR_ADDR, bytes([0xEC, 0x05]))
    return i2c.readfrom(SCD41_SENSOR_ADDR, 9) # Responseの欄の値すべてで合計9バイト読み取る

def is_data_crc_correct(data):
    for i in range(3):
        # CRCのデータを配列から抽出する
        expected_crc = data[3*i + 2]
        # チェックサムアルゴリズムを利用する
        calculated_crc = generate_crc(data[3*i:3*i+2])
        if expected_crc != calculated_crc:
            print(f"SCD41: CRC ERROR at word number {i}")
            return False
    return True

def calculate_and_show_data(raw):
    # co2は格納された値をそのまま利用できる
    co2 = int.from_bytes(raw[0:2], 'big') # 0から1までの要素0x01f4
    # raw[2]はCRC of 0x7b(10111011 8bit=1byte)
    raw_temperature = int.from_bytes(raw[3:5], 'big') # 3から4までの要素0x6667
    # raw[5]はCRC of 0xa2
    raw_humidity = int.from_bytes(raw[6:8], 'big') # 6から7までの要素0x5eb9
    # raw[8]はCRC of 0x3c

    temperature = -45 + 175 * (raw_temperature / 65535.0) # T = - 45 + 175 * word[1](=Temp) / 2^16
    humidity = 100 * (raw_humidity / 65535.0) # RH = 100 * word[2](=RH) / 2^16

    print(f"SCD41: CO2: {co2} ppm, Temperature: {temperature:.02f} C, Humidity: {humidity:.02f} %")

def poll_sensor():
    if not get_data_ready_status():
        print("SCD41: No new data available")
        return
    measurements = read_measurement()
    if is_data_crc_correct(measurements):
        calculate_and_show_data(measurements)
    else:
        print("SCD41: CRC error!")

def main():
    stop_periodic_measurements()
    time.sleep(1)  # Delay for 1 second
    start_periodic_measurements()
    print("SCD41: Initialization finished")

    while True:
        time.sleep(1)  # Poll every second
        poll_sensor()

if __name__ == "__main__":
    main()
