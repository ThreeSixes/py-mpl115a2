# mpl115a2 class by ThreeSixes (https://github.com/ThreeSixes/py-mpl115a2)

###########
# Imports #
###########

import time
import quick2wire.i2c as qI2c
from pprint import pprint

##################
# mpl115a2 class #
##################

class mpl115a2:
    """
    mpl115a2 is a class that supports communication with an I2C-connected Freescale MPL115A2 barometer. The constructor for this class accepts one argement:

    mpl115a2Addr: The I2C address of the sensor, but will default to 0x60 if it's not specified.
    """

    # The barometer config variables are based on the MPL115A2 datasheet
    # http://www.adafruit.com/datasheets/MPL115A2.pdf

    def __init__(self, mpl115a2Addr = 0x60):
        # I2C set up class-wide I2C bus
        self.__i2c = qI2c
        self.__i2cMaster = qI2c.I2CMaster()
        
        # Set global address var
        self.__addr = mpl115a2Addr
        
        # Registers
        self.regPadcMSB =  0x00
        self.regPadcLSB =  0x01
        self.regTadcMSB =  0x02
        self.regTadcLSB =  0x03
        self.regA0MSB   =  0x04
        self.regA0LSB   =  0x05
        self.regB1MSB   =  0x06
        self.regB1LSB   =  0x07
        self.regB2MSB   =  0x08
        self.regB2LSB   =  0x09
        self.regC12MSB  =  0x0a
        self.regC12LSB  =  0x0b
        self.regConvert =  0x12

    def __readReg(self, register):
        """
        __readReg(register)
        
        Read a given register from the MPL115A2.
        """
        
        data = 0
        
        try:
            # Read the specific register.
            res = self.__i2cMaster.transaction(self.__i2c.writing_bytes(self.__addr, register), self.__i2c.reading(self.__addr, 1))
            data = ord(res[0])
            
        except IOError:
            raise IOError("mpl115a2 IO Error: Failed to read MPL115A2 sensor on I2C bus.")
            
        return data
    
    def __readRegRange(self, regStart, regEnd):
        """
        __readRegRange(regStart, regEnd)
        
        Reads a continuous range of registers from regStart to regEnd. Returns an array of integers.
        """
        
        regRange = ""
        
        # Figure out how many bytes we'll be reading.
        regCount = (regEnd - regStart) + 1
        
        # Read a range of registers.
        regRange = self.__i2cMaster.transaction(self.__i2c.writing_bytes(self.__addr, regStart), self.__i2c.reading(self.__addr, regCount))
        
        # Convert returned data to byte array.
        regRange = bytearray(regRange[0])
        
        return regRange
    
    def __writeReg(self, register, byte):
        """
        __writeReg(register, byte)
        
        Write a given byte to a given register to the MPL115A2
        """
        
        try:
            self.__i2cMaster.transaction(self.__i2c.writing_bytes(self.__addr, register, byte))
        except IOError:
            raise IOError("mpl115a2 IO Error: Failed to write to MPL115A2 sensor on I2C bus.")
    
    def __getSigned(self, unsigned, bits = 16):
        """
        __getSigned(unsigned, [bits = 16])
        
        Converts an unsigned number to a two's compliment signed number.  Bits is the length of the number, and defaults to 16 if not specified.
        """
        
        # Placed holder for our signed number.
        signed = 0
        
        # If we have the sign bit set remove it and drop the numbe below the zero line.
        if (unsigned & (1 << (bits - 1))) != 0:
            signed = unsigned - (1 << bits)
        # If not, the nubmer is positive and we don't need to do anything.
        else:
            signed = unsigned
        
        return signed
        
    def getPressTemp(self):
        """
        getPressTemp()
        
        Gets the barometirc pressure and temperature from the sensor. Returns an integer integer representing a pressure in kPa between 50 and 115, and degrees celcius.
        """
        
        # Set return value [pressure, temp]
        retVal = [0, 0]
        
        # Get the coefficients
        coefficientBytes = self.__readRegRange(self.regA0MSB, self.regC12LSB)
        
        a0  = (coefficientBytes[0] << 8) | coefficientBytes[1]
        b1  = (coefficientBytes[2] << 8) | coefficientBytes[3]
        b2  = (coefficientBytes[4] << 8) | coefficientBytes[5]
        # C12 needs is stored in the device registers shifted two bits to the left. Compensate.
        c12 = (((coefficientBytes[6] << 8) | coefficientBytes[7]) >> 2)
        
        # Send conversion start command by writing 0x00 to the convert register.
        self.__writeReg(self.regConvert, 0x00)
        
        # Wait for conversion.
        time.sleep(0.04)
        
        # And get the ADC counter
        adcBytes = self.__readRegRange(self.regPadcMSB, self.regTadcLSB)
        
        # Get ADC values - 10 bit with MSB lined up at 16 bit register's MSB. Compensate.
        pAdc  = (((adcBytes[0] << 8) | adcBytes[1]) >> 6)
        tAdc  = (((adcBytes[2] << 8) | adcBytes[3]) >> 6)
        
        # Convert the unsigned ints to two's compliment nubmers.
        a0 = self.__getSigned(a0)
        b1 = self.__getSigned(b1)
        b2 = self.__getSigned(b2)
        c12 = self.__getSigned(c12, 14)
        
        # Scale our coefficients' LSB
        a0 = a0 / 8.0 # 3 decimal bits. 2^3 = 8
        b1 = b1 / 8192.0 # 13 decimal bits. 2^13 = 8192
        b2 = b2 / 16384.0 # 14 decimal bits. 2^14 = 16384
        c12 = c12 / 4194304.0
        
        # Compute compensated pressure.
        pComp = a0 + (b1 + c12 * tAdc) * pAdc + b2 * tAdc
        retVal[0] = round((pComp * (65.0 / 1023.0) + 50), 2)
        
        # Compute temperature.
        retVal[1] = round(((tAdc - 498.0) / -5.35 + 25.0), 1)
        
        return retVal
    
    def setReg(self, register, value):
        """
        setReg(register, value)
        
        Manuall set the value of a given register. The writable registers on this chip are regCfgA (0x00), regCfgB (0x01), and regMode (0x02).
        """
        
        # Make sure we're trying to write to a R/W register
        if (register >= self.regCfgA) and (register <= self.regMode):
            self.__writeReg(register, value)
        else:
            raise ValueError("MPL115A2 register must be writable to set it.")
    
