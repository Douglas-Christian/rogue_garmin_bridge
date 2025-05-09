4.9 Indoor Bike Data 
The Indoor Bike Data characteristic is used to send training-related data to the Client from an indoor bike 
(Server). Included in the characteristic value is a Flags field (for showing the presence of optional fields), 
and depending upon the contents of the Flags field, it may include one or more optional fields as defined 
on the Bluetooth SIG Assigned Numbers webpage [2]. 
Bluetooth SIG Proprietary 
Page 42 of 78 
Fitness Machine Service  /  Service Specification 
4.9.1 Characteristic Behavior 
When the Indoor Bike Data characteristic is configured for notification via the Client Characteristic 
Configuration descriptor and training-related data is available, this characteristic shall be notified. The 
Server should notify this characteristic at a regular interval, typically once per second while in a 
connection and the interval is not configurable by the Client. 
For low energy, all the fields of this characteristic cannot be present simultaneously if using a default 
ATT_MTU size. Refer to Sections 4.1 and 4.19 for additional requirements on the transmission of a Data 
Record in multiple notifications. Refer to Section 4.18 for additional requirements on time-sensitive data. 
For BR/EDR, this restriction does not exist due to a larger MTU size. 
4.9.1.1 Flags Field 
The Flags field shall be included in the Indoor Bike Data characteristic. 
Reserved for Future Use (RFU) bits in the Flags fields shall be set to 0. 
The bits of the Flags field and relationship to bits in the Fitness Machine Feature characteristic are shown 
in Table 4.10. 
Flags Bit Name 
When Set to 0 
When Set to 1 
More Data (bit 0), see 
Sections 4.9.1.2 and 4.19. 
Instantaneous 
Speed field 
present 
Corresponding Fitness 
Machine Feature Support bit 
(see Section 4.3) 
Instantaneous 
Speed fields 
not present 
Average Speed present (bit 1), 
see Section 4.9.1.3. 
Corresponding 
field not present 
None 
Corresponding 
field present 
Instantaneous Cadence (bit 
2), see Section 4.9.1.4. 
Corresponding 
fields present 
Average Speed Supported (bit 0) 
Corresponding 
fields not 
present 
Average Cadence present (bit 
3), see Section 4.9.1.5. 
Corresponding 
field not present 
Cadence Supported (bit 1) 
Corresponding 
field present 
Total Distance Present (bit 4), 
see Section 4.9.1.6. 
Corresponding 
field not present 
Cadence Supported (bit 1) 
Corresponding 
field present 
Resistance Level Present (bit 
5), see Section 4.9.1.7. 
Corresponding 
field not present 
Corresponding 
field present 
Total Distance Supported (bit 2) 
Resistance Level Supported (bit 
7) 
Instantaneous Power Present 
(bit 6), see Section 4.9.1.8. 
Corresponding 
field not present 
Corresponding 
field present 
Power Measurement Supported 
(bit 14) 
Average Power Present (bit 
7), see Section 4.9.1.9. 
Corresponding 
field not present 
Corresponding 
field present 
Power Measurement Supported 
(bit 14) 
Expended Energy Present (bit 
8), see Sections 4.9.1.10, 
4.9.1.11 and 4.9.1.12. 
Corresponding 
fields not 
present 
Corresponding 
fields present 
Expended Energy Supported (bit 
9) 
Bluetooth SIG Proprietary 
Page 43 of 78 
Fitness Machine Service  /  Service Specification 
Heart Rate Present (bit 9, see 
Section 4.9.1.13. 
Corresponding 
field not present 
Corresponding 
field present 
Heart Rate Measurement 
Supported (bit 10) 
Metabolic Equivalent Present 
(bit 10), see Section 4.9.1.14. 
Corresponding 
field not present 
Corresponding 
field not present 
Corresponding 
field present 
Metabolic Equivalent Supported 
(bit 11) 
Elapsed Time Present (bit 11), 
see Section 4.9.1.15. 
Remaining Time Present (bit 
12), see Section 4.9.1.16. 
Corresponding 
field present 
Corresponding 
field not present 
Elapsed Time Supported (bit 12) 
Remaining Time Supported (bit 
13) 
Corresponding 
field present 
Table 4.10: Bit Definitions for the Indoor Bike Data Characteristic 
4.9.1.2 Instantaneous Speed Field 
The Instantaneous Speed field shall be included in the indoor bike-related Data Record. If the Data 
Record is split into several notifications of the Indoor Bike Data, this field shall only be included in the 
Indoor Bike Data characteristic when the More Data bit of the Flags field is set to 0. Refer to Section 4.19 
for additional information related to the transmission of a Data Record. 
The Instantaneous Speed field represents the instantaneous speed of the user. 
4.9.1.3 Average Speed Field 
The Average Speed field may be included in the Indoor Bike Data characteristic if the device supports the 
Average Speed feature (see Table 4.10). 
The Average Speed field represents the average speed since the beginning of the training session. 
4.9.1.4 Instantaneous Cadence Field 
The Instantaneous Cadence field may be included in the Indoor Bike Data characteristic if the device 
supports the Cadence feature (see Table 4.10). 
The Instantaneous Cadence field represents the instantaneous cadence of the user. 
4.9.1.5 Average Cadence Field 
The Average Cadence field may be included in the Indoor Bike Data characteristic if the device supports 
the Cadence feature (see Table 4.10). 
The Average Speed field represents the average cadence since the beginning of the training session. 
4.9.1.6 Total Distance Field 
The Total Distance field may be included in the Indoor Bike Data characteristic if the device supports the 
Total Distance feature (see Table 4.10). 
The Total Distance field represents the total distance reported by the Server since the beginning of the 
training session. 
4.9.1.7 Resistance Level 
The Resistance Level field may be included in the Indoor Bike Data characteristic if the device supports 
the Resistance Level feature (see Table 4.10). 
Bluetooth SIG Proprietary 
Page 44 of 78 
Fitness Machine Service  /  Service Specification 
The Resistance Level field represents the value of the current value of the resistance level of the Server. 
4.9.1.8 Instantaneous Power 
The Instantaneous Power field may be included in the Indoor Bike Data characteristic if the device 
supports the Power Measurement feature (see Table 4.10). 
The Instantaneous Power field represents the value of the instantaneous power measured by the Server. 
4.9.1.9 Average Power 
The Average Power field may be included in the Indoor Bike Data characteristic if the device supports the 
Power Measurement feature (see Table 4.10). 
The Average Power field represents the value of the average power measured by the Server since the 
beginning of the training session. 
4.9.1.10 Total Energy Field 
The Total Energy field may be included in the Indoor Bike Data characteristic if the device supports the 
Expended Energy feature (see Table 4.10). 
The Total Energy field represents the total expended energy of a user since the training session has 
started. 
If this field has to be present (i.e., if the Expended Energy Present bit of the Flags field is set to 1) but the 
Server does not support the calculation of the Total Energy, the Server shall use the special value 
0xFFFF (i.e., decimal value of 65535 in UINT16 format), which means ‘Data Not Available’. 
4.9.1.11 Energy per Hour Field 
The Energy per Hour field may be included in the Indoor Bike Data characteristic if the device supports 
the Expended Energy feature (see Table 4.10). 
The Energy per Hour field represents the average expended energy of a user during a period of one hour. 
If this field has to be present (i.e., if the Expended Energy Present bit of the Flags field is set to 1) but the 
Server does not support the calculation of the Energy per Hour, the Server shall use the special value 
0xFFFF (i.e., decimal value of 65535 in UINT16 format), which means ‘Data Not Available’. 
4.9.1.12 Energy per Minute Field 
The Energy per Minute field may be included in the Indoor Bike Data characteristic if the device supports 
the Expended Energy feature (see Table 4.10). 
The Energy per Minute field represents the average expended energy of a user during a period of one 
minute. 
If this field has to be present (i.e., if the Expended Energy Present bit of the Flags field is set to 1) but the 
Server does not support the calculation of the Energy per Minute, the Server shall use the special value 
0xFF (i.e., decimal value of 255 in UINT16 format), which means ‘Data Not Available’. 
Bluetooth SIG Proprietary 
Page 45 of 78 
Fitness Machine Service  /  Service Specification 
4.9.1.13 Heart Rate Field 
The Heart Rate field may be included in the Indoor Bike Data characteristic if the device supports the 
Heart Rate feature (see Table 4.10). 
The Heart Rate field represents the current heart rate value of the user (e.g., measured via the contact 
heart rate or any other means). 
4.9.1.14 Metabolic Equivalent Field 
The Metabolic Equivalent field may be included in the Indoor Bike Data characteristic if the device 
supports the Metabolic Equivalent feature (see Table 4.10). 
The Metabolic Equivalent field represents the metabolic equivalent of the user. 
4.9.1.15 Elapsed Time Field 
The Elapsed Time field may be included in the Indoor Bike Data characteristic if the device supports the 
Elapsed Time feature (see Table 4.10). 
The Elapsed Time field represents the elapsed time of a training session since the training session has 
started (See Section 4.2).  
Refer to Sections 4.1 and 4.18 for additional requirements on the presence of this field for the case where 
a Data Record is sent in multiple notifications. 
4.9.1.16 Remaining Time Field 
The Remaining Time field may be included in the Indoor Bike Data characteristic if the device supports 
the Remaining Time feature (see Table 4.10). 
The Remaining Time field represents the remaining time of a selected training session.  
4.10 Training Status 
The Training Status characteristic shall be used by the Server to send the training status information to 
the Client. Included in the characteristic value is a Flags field (for showing the presence of optional fields), 
a Training Status field, and depending upon the contents of the Flags field, also a Training Status String. 
The structure of the characteristic is defined below: 
LSO 
Flags 
MSO 
Training Status 
Training Status 
String 
(if present) 
Octet Order 
N/A 
N/A 
Data type 
LSO…MSO 
8bit 
8bit 
Size 
UTF8 String 
1 octet 
1 octet 
Units 
Variable 
None 
None 
Table 4.11: Structure of the Training Status Characteristic 
None 
Bluetooth SIG Proprietary 
Page 46 of 78 
Fitness Machine Service  /  Service Specification 
4.10.1 Characteristic Behavior 
When the Training Status characteristic is configured for notification via the Client Characteristic 
Configuration descriptor and a new training status is available (e.g., when there is a transition in the 
training program), this characteristic shall be notified. 
When read, the Training Status characteristic returns a value that is used by a Client to determine the 
current training status of the Server. 
The Training Status characteristic contains time-sensitive data, thus the requirements for time-sensitive 
data and data storage defined in Section 4.18 apply. 
4.10.1.1 Flags Field 
The Flags field shall be included in the Training Status characteristic. 
Reserved for Future Use (RFU) bits in the Flags fields shall be set to 0. 
The bits of the Flags field and their function are shown in Table 4.12. 
Bit 
Definition 
0 
Training Status String present: 
0 = False 
1 = True 
1 
Extended String present: 
0 = False 
1 = True 
2-7 
Reserved for Future Use 
Table 4.12: Bit Definitions for the Training State Characteristic 
For low energy, the Training Status characteristic may exceed the current MTU size (i.e., if the Training 
Status String field exceeds the negotiated MTU size minus 5 octets). If the characteristic size exceeds the 
current MTU size, the Server shall set the Extended String bit of the Flags field to 1 to inform the Client 
that additional characters are available and should be read via the appropriate GATT procedure (e.g., 
GATT Read Long procedure). The Server should not update the value more than once in a ten seconds 
period if the Extended String present bit is set to 1 in order to give enough time to the Client to read this 
value. Only the first (ATT_MTU-3) octets of the characteristic value can be included in a notification, but 
the entire string may be read by using the GATT Read Long sub-procedure. 
For BR/EDR, this restriction does not exist due to a larger MTU size. 
4.10.1.2 Training Status Field 
The Training Status field shall be included in the Training Status characteristic. 
The Training Status field represents the current training state while a user is exercising. The values of the 
Training Status field are defined in Table 4.13. 
Bluetooth SIG Proprietary 
Page 47 of 78 
Fitness Machine Service  /  Service Specification 
Value 
Definition 
0x00 
Other 
0x01 
Idle 
0x02 
Warming Up 
0x03 
Low Intensity Interval 
0x04 
High Intensity Interval 
0x05 
Recovery Interval 
0x06 
Isometric 
0x07 
Heart Rate Control 
0x08 
Fitness Test 
0x09 
Speed Outside of Control Region - Low (increase speed to return to controllable 
region) 
0x0A 
Cool Down 
Speed Outside of Control Region - High (decrease speed to return to controllable 
region) 
0x0B 
0x0C 
Watt Control 
0x0D 
Manual Mode (Quick Start) 
0x0E 
Pre-Workout 
0x0F 
Post-Workout 
0x10-0xFF 
Reserved for Future Use 
Table 4.13: Training Status Field Definition 
4.10.1.3 Training Status String Field 
The Training Status String field may be included in the Training Status characteristic. 
The Training Status String field is a string-based field that can be used to give more specific information 
related to the training status.  
4.11 Supported Speed Range 
The Supported Speed Range characteristic shall be exposed by the Server if the Speed Target Setting 
feature is supported. 
The Supported Speed Range characteristic is used to send the supported speed range as well as the 
minimum speed increment supported by the Server. Included in the characteristic value are a Minimum 
Speed field, a Maximum Speed field, and a Minimum Increment field as defined on the Bluetooth SIG 
Assigned Numbers webpage [2]. 
4.11.1 Characteristic Behavior 
When read, the Supported Speed Range characteristic returns a value that is used by a Client to 
determine the valid range that can be used in order to control the speed of the Server. 
Bluetooth SIG Proprietary 
Page 48 of 78 
Fitness Machine Service  /  Service Specification 
4.12 Supported Inclination Range 
The Supported Inclination Range characteristic shall be exposed by the Server if the Inclination Target 
Setting feature is supported. 
The Supported Inclination Range characteristic is used to send the supported inclination range as well as 
the minimum inclination increment supported by the Server. Included in the characteristic value are a 
Minimum Inclination field, a Maximum Inclination field, and a Minimum Increment field as defined on the 
Bluetooth SIG Assigned Numbers webpage [2]. 
4.12.1 Characteristic Behavior 
When read, the Supported Inclination Range characteristic returns a value that is used by a Client to 
determine the valid range that can be used in order to control the inclination of the Server. 
4.13 Supported Resistance Level Range 
The Supported Resistance Level Range characteristic shall be exposed by the Server if the Resistance 
Control Target Setting feature is supported. 
The Supported Resistance Level Range characteristic is used to send the supported resistance level 
range as well as the minimum resistance increment supported by the Server. Included in the 
characteristic value are a Minimum Resistance Level field, a Maximum Resistance Level field, and a 
Minimum Increment field as defined on the Bluetooth SIG Assigned Numbers webpage [2]. 
4.13.1 Characteristic Behavior 
When read, the Supported Resistance Level Range characteristic returns a value that is used by a Client 
to determine the valid range that can be used in order to control the resistance level of the Server. 
4.14 Supported Power Range 
The Supported Power Range characteristic shall be exposed by the Server if the Power Target Setting 
feature is supported. 
The Supported Power Range characteristic is used to send the supported power range as well as the 
minimum power increment supported by the Server. Included in the characteristic value are a Minimum 
Power field, a Maximum Power field, and a Minimum Increment field as defined on the Bluetooth SIG 
Assigned Numbers webpage [2]. Note that the Minimum Power field and the Maximum Power field 
represent the extreme values supported by the Server and are not related to, for example, the current 
speed of the Server. 
4.14.1 Characteristic Behavior 
When read, the Supported Power Range characteristic returns a value that is used by a Client to 
determine the valid range that can be used in order to control the power reference of the Server. 
4.15 Supported Heart Rate Range 
The Supported Heart Rate Range characteristic shall be exposed by the Server if the Heart Rate Target 
Setting feature is supported.  
Bluetooth SIG Proprietary 
Page 49 of 78 
Fitness Machine Service  /  Service Specification 
The Supported Heart Rate Range characteristic is used to send the supported Heart Rate range as well 
as the minimum Heart Rate increment supported by the Server. Included in the characteristic value are a 
Minimum Heart Rate field, a Maximum Heart Rate field, and a Minimum Increment field as defined on the 
Bluetooth SIG Assigned Numbers webpage [2]. 
4.15.1 Characteristic Behavior 
When read, the Supported Heart Rate Range characteristic returns a value that is used by a Client to 
determine the valid range that can be used in order to set the heart rate target for a given training 
session. 
4.16 Fitness Machine Control Point 
The Server may expose the Fitness Machine Control Point. 
The Fitness Machine Control Point characteristic is used to request a specific function to be executed on 
the Server. 
The format of the Fitness Machine Control Point characteristic is defined in Table 4.14. 
LSO 
Op Code 
(see Table 4.15) 
MSO 
Parameter 
(see Table 4.15) 
Byte Order 
N/A 
LSO...MSO 
Data type 
UINT8 
Variable 
Size 
1 octet 
0 to 18 octets 
Units 
None 
None 
Table 4.14: Fitness Machine Control Point Characteristic Format 
The Op Codes, Parameters, and requirements for the Fitness Machine Control Point are defined in 
Section 4.16.1. 
4.16.1 Fitness Machine Control Point Procedure Requirements 
A Client shall use the GATT Write Characteristic Value sub-procedure to initiate a procedure defined in 
Table 4.15. 
The Op Codes, Parameters, and their requirements are defined in Table 4.15. 
Op Code 
Value 
Requirement 
Definition 
Parameter Value 
Description 
0x00 
M 
Request Control 
N/A 
Initiates the procedure to 
request the control of a fitness 
machine. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
Bluetooth SIG Proprietary 
Page 50 of 78 
 Fitness Machine Service  /  Service Specification 
Bluetooth SIG Proprietary Page 51 of 78 
Op Code 
Value 
Requirement Definition Parameter Value Description 
0x01 M Reset, 
see Section 
4.16.2.2 
N/A Initiates the procedure to reset 
the controllable settings of a 
fitness machine. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x02 C.1 Set Target Speed, 
see Section 
4.16.2.3 
Target Speed,  
UINT16, in km/h 
with a resolution of 
0.01 km/h 
Initiate the procedure to set the 
target speed of the Server. The 
desired target speed is sent as 
parameters to this op code. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x03 C.2 Set Target 
Inclination, 
see Section 
4.16.2.4 
Target Inclination,  
SINT16, in Percent 
with a resolution of 
0.1 % 
Initiate the procedure to set the 
target inclination of the Server. 
The desired target inclination is 
sent as parameters to this op 
code. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x04 C.3 Set Target 
Resistance Level, 
see Section 
4.16.2.5 
Target Resistance 
Level,  
UINT8, unitless 
with a resolution of 
0.1. 
Initiate the procedure to set the 
target resistance level of the 
Server. The desired target 
resistance level is sent as 
parameters to this op code. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x05 C.4 Set Target Power, 
see Section 
4.16.2.6 
Target Power,  
SINT16, in Watt 
with a resolution of 
1 W. 
Initiate the procedure to set the 
target power of the Server. The 
desired target power is sent as 
parameters to this op code. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
 Fitness Machine Service  /  Service Specification 
Bluetooth SIG Proprietary Page 52 of 78 
Op Code 
Value 
Requirement Definition Parameter Value Description 
0x06 C.5 Set Target Heart 
Rate, 
see Section 
4.16.2.7 
Target Heart Rate,  
UINT8, in BPM 
with a resolution of 
1 BPM. 
Initiate the procedure to set the 
target heart rate of the Server. 
The desired target heart rate is 
sent as parameters to this op 
code. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x07 M Start or Resume, 
see Section 
4.16.2.8 
N/A Initiate the procedure to start or 
resume a training session on 
the Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x08 M Stop or Pause, 
see Section 
4.16.2.9 
Control 
Information, see 
Section 4.16.2.9. 
Initiate the procedure to stop or 
pause a training session on the 
Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x09 C.6 Set Targeted 
Expended Energy, 
see Section 
4.16.2.10 
Targeted 
Expended Energy,  
UINT16, in 
Calories with a 
resolution of 1 
Calorie. 
Set the targeted expended 
energy for a training session on 
the Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x0A C.7 Set Targeted 
Number of Steps, 
see Section 
4.16.2.11 
Targeted Number 
of Steps,  
UINT16, in Steps 
with a resolution of 
1 Step. 
Set the targeted number of 
steps for a training session on 
the Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
 Fitness Machine Service  /  Service Specification 
Bluetooth SIG Proprietary Page 53 of 78 
Op Code 
Value 
Requirement Definition Parameter Value Description 
0x0B C.8 Set Targeted 
Number of 
Strides, see 
Section 4.16.2.12 
Targeted Number 
of Strides,  
UINT16, in Stride 
with a resolution of 
1 Stride. 
Set the targeted number of 
strides for a training session on 
the Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x0C C.9 Set Targeted 
Distance, see 
Section 4.16.2.13 
Targeted Distance,  
UINT24, in Meters 
with a resolution of 
1 Meter. 
Set the targeted distance for a 
training session on the Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x0D C.10 Set Targeted 
Training Time, 
see Section 
4.16.2.14 
Targeted Training 
Time,  
UINT16, in 
Seconds with a 
resolution of 1 
Second. 
Set the targeted training time 
for a training session on the 
Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x0E C.11 Set Targeted 
Time in Two Heart 
Rate Zones, see 
Section 4.16.2.15 
Targeted Time 
Array, see Section 
4.16.2.15. 
Set the targeted time in two 
heart rate zones for a training 
session on the Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x0F C.12 Set Targeted 
Time in Three 
Heart Rate Zones, 
see Section 
4.16.2.16 
Targeted Time 
Array, see Section 
4.16.2.16. 
Set the targeted time in three 
heart rate zones for a training 
session on the Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x10 C.13 Set Targeted 
Time in Five Heart 
Rate Zones, see 
Section 4.16.2.17 
Targeted Time 
Array, see Section 
4.16.2.17. 
Set the targeted time in five 
heart rate zones for a training 
session on the Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
 Fitness Machine Service  /  Service Specification 
Bluetooth SIG Proprietary Page 54 of 78 
Op Code 
Value 
Requirement Definition Parameter Value Description 
0x11 C.14 Set Indoor Bike 
Simulation 
Parameters, see 
Section 4.16.2.18 
Simulation 
Parameter Array, 
see Section 
4.16.2.18 
Set the simulation parameters 
for a training session on the 
Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x12 O Set Wheel 
Circumference, 
see Section 
4.16.2.19 
Wheel 
Circumference, 
UINT16, in 
Millimeters with 
resolution of 0.1 
Millimeter 
Set the wheel circumference for 
a training session on the 
Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x13 O Spin Down 
Control, see 
Section 4.16.2.20 
Control Parameter, 
see Section 
4.16.2.20 
Control the spin down 
procedure of a Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x14 C.15 Set Targeted 
Cadence 
Targeted Cadence,  
UINT16, in 
1/minute with a 
resolution of 0.5 
1/minute. 
Set the targeted cadence for a 
training session on the Server. 
The response to this control 
point is Op Code 0x80 followed 
by the appropriate Parameter 
Value. 
0x15-0x7F N/A Reserved for 
Future Use 
N/A N/A 
0x80 M Response Code, 
see Section 
4.16.2.22 
See Section 
4.16.2.22 
Used to identify the response to 
this Control Point. 
0x81-0xFF N/A Reserved for 
Future Use 
N/A N/A 
Table 4.15: Fitness Machine Control Point Procedure Requirements 
C.1: Mandatory to support if the Speed Target Setting feature is supported; otherwise Excluded. 
C.2: Mandatory to support if the Inclination Target Setting feature is supported; otherwise Excluded. 
C.3: Mandatory to support if the Resistance Target Setting feature is supported; otherwise Excluded. 
C.4: Mandatory to support if the Power Target Setting feature is supported; otherwise Excluded. 
C.5: Mandatory to support if the Heart Rate Target Setting feature is supported; otherwise Excluded. 
C.6: Mandatory to support if the Targeted Energy Expended Configuration feature is supported; otherwise Excluded. 
C.7: Mandatory to support if the Targeted Number of Steps Configuration feature is supported; otherwise Excluded. 
Fitness Machine Service  /  Service Specification 
C.8: Mandatory to support if the Targeted Number of Strides Configuration feature is supported; otherwise Excluded. 
C.9: Mandatory to support if the Targeted Distance Configuration feature is supported; otherwise Excluded. 
C.10: Mandatory to support if the Targeted Training Time Configuration feature is supported; otherwise Excluded. 
C.11: Mandatory to support if the Targeted Time in Two Heart Rate Zones Configuration feature is supported; 
otherwise Excluded. 
C.12: Mandatory to support if the Targeted Time in Three Heart Rate Zones Configuration feature is supported; 
otherwise Excluded. 
C.13: Mandatory to support if the Targeted Time in Five Heart Rate Zones Configuration feature is supported; 
otherwise Excluded. 
C.14: Mandatory to support if the Indoor Bike Simulation Parameters feature is supported; otherwise Excluded.  
C.15: Mandatory to support if the Set Targeted Cadence feature is supported; otherwise Excluded. 
4.16.2 Fitness Machine Control Point Behavioral Description 
The Fitness Machine Control Point is used by a Client to control certain behaviors of the Server. 
Procedures are triggered by a Write to this characteristic value that includes an Op Code specifying the 
operation (see Table 4.15), which may be followed by a Parameter that is valid within the context of that 
Op Code. 
Each procedure defined in Sections 4.16.2.2 to 4.16.2.20 requires control permission from the Server. 
The Request Control procedure defined in Section 4.16.2.1 is used to request the control of the Server. 
4.16.2.1 Request Control Procedure 
When the Request Control Op Code is written to the Fitness Machine Control Point and the Result Code 
is ‘Success’, the Server shall allow the Client to perform any supported control procedures (see Sections 
4.16.2.2 to 4.16.2.20). 
The response shall be indicated when the Reset Procedure is completed using the Response Code Op 
Code and the Request Op Code, along with the appropriate Result Code as defined in Section 4.16.2.22.  
The control permission remains valid until the connection is terminated, the notification of the Fitness 
Machine Status is sent with the value set to Control Permission Lost (see Section 4.17), or the Reset 
procedure (see Section 4.16.2.2) is initiated by the Client. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.2 Reset Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Reset Op Code is written to the Fitness Machine Control Point and the Result Code is 
‘Success’, the Server shall set the control parameters to their respective default values (e.g., target speed 
set to 0, inclination set to 0). In addition, if the Fitness Machine supports the Remaining Time and 
Elapsed Time features, it shall set the time-related fields to 0. The Training Status characteristic value 
shall also be set to Idle (0x01). 
Bluetooth SIG Proprietary 
Page 55 of 78 
Fitness Machine Service  /  Service Specification 
The response shall be indicated when the Reset Procedure is completed using the Response Code Op 
Code, the Request Op Code, along with the appropriate Result Code as defined in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.3 Set Target Speed Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Target Speed Op Code is written to the Fitness Machine Control Point and the Result Code 
is ‘Success’, the Server shall set the Target Speed to the value sent as a Parameter. 
The response shall be indicated when the Set Target Speed Procedure is completed using the Response 
Code Op Code and the Request Op Code, along with the appropriate Result Code as defined in Section 
4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.4 Set Target Inclination Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Target Inclination Op Code is written to the Fitness Machine Control Point and the Result 
Code is ‘Success’, the Server shall set the target inclination to the value sent as a Parameter. A positive 
value means that the user will feel as if they are going uphill and a negative value means that the user will 
feel as if they are going downhill. 
The response shall be indicated when the Set Target Inclination Procedure is completed using the 
Response Code Op Code and the Request Op Code, along with the appropriate Result Code as defined 
in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.5 Set Target Resistance Level Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Target Resistance Level Op Code is written to the Fitness Machine Control Point and the 
Result Code is ‘Success’, the Server shall set the target resistance level to the value sent as a 
Parameter. 
Bluetooth SIG Proprietary 
Page 56 of 78 
Fitness Machine Service  /  Service Specification 
The response shall be indicated when the Set Target Resistance Level Procedure is completed using the 
Response Code Op Code and the Request Op Code, along with the appropriate Result Code as defined 
in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.6 Set Target Power Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Target Power Op Code is written to the Fitness Machine Control Point and the Result Code 
is ‘Success’, the Server shall set the target power to the value sent as a Parameter. 
The response shall be indicated when the Set Target Power Procedure is completed using the Response 
Code Op Code and the Request Op Code, along with the appropriate Result Code as defined in Section 
4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.7 Set Target Heart Rate Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Target Heart Rate Op Code is written to the Fitness Machine Control Point and the Result 
Code is ‘Success’, the Server shall set the target heart rate to the value sent as a Parameter. 
The response shall be indicated when the Set Target Heart Rate Procedure is completed using the 
Response Code Op Code and the Request Op Code, along with the appropriate Result Code as defined 
in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.8 Start or Resume Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Start or Resume Op Code is written to the Fitness Machine Control Point and the Result Code 
is ‘Success’, the Server shall initiate the start procedure of the Fitness Machine. 
If the Fitness Machine supports the Remaining Time and Elapsed Time features, the Fitness Machine 
shall update the related Remaining Time and Elapsed Time fields at a regular interval (e.g., every 
second). In order to set the time-related fields to zero, the Reset procedure defined in Section 4.16.2.2 
shall be used. 
Bluetooth SIG Proprietary 
Page 57 of 78 
Fitness Machine Service  /  Service Specification 
The response shall be indicated when the Start or Resume Procedure is completed using the Response 
Code Op Code and the Request Op Code, along with the appropriate Result Code as defined in Section 
4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.9 Stop or Pause Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Stop or Pause Op Code is written to the Fitness Machine Control Point and the Result Code is 
‘Success’, the Server shall initiate the stop or pause procedure of the Fitness Machine depending on the 
Control Information Parameter value. The format of the Control Information Parameter value is UINT8, 
and the supported values are defined in the table below: 
Value 
Control Information 
0x00 
Reserved for Future Use 
0x01 
Stop 
0x02 
Pause 
0x03-0xFF Reserved for Future Use 
Table 4.16: Control Information Parameter Value for Stop or Pause Procedure 
If the Fitness Machine supports the Remaining Time and Elapsed Time features, the Fitness Machine 
shall stop updating the related Remaining Time and Elapsed Time fields. In order to set the time-related 
fields to zero, the Reset procedure defined in Section 4.16.2.2 shall be used. 
The response shall be indicated when the Stop or Pause Procedure is completed using the Response 
Code Op Code and the Request Op Code, along with the appropriate Result Code as defined in Section 
4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.10 Set Targeted Expended Energy Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Targeted Expended Energy Op Code is written to the Fitness Machine Control Point and 
the Result Code is ‘Success’, the Server shall use the value sent as a Parameter as the new targeted 
expended energy. 
The response shall be indicated when the Set Targeted Expended Energy Procedure is completed using 
the Response Code Op Code and the Request Op Code, along with the appropriate Result Code as 
defined in Section 4.16.2.22. 
Bluetooth SIG Proprietary 
Page 58 of 78 
Fitness Machine Service  /  Service Specification 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.11 Set Targeted Number of Steps Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Targeted Number of Steps Op Code is written to the Fitness Machine Control Point and the 
Result Code is ‘Success’, the Server shall use the value sent as a Parameter as the new targeted number 
of steps. 
The response shall be indicated when the Set Targeted Number of Steps Procedure is completed using 
the Response Code Op Code and the Request Op Code, along with the appropriate Result Code as 
defined in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.12 Set Targeted Number of Strides Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Targeted Number of Strides Op Code is written to the Fitness Machine Control Point and 
the Result Code is ‘Success’, the Server shall use the value sent as a Parameter as the new targeted 
number of strides. 
The response shall be indicated when the Set Targeted Number of Strides Procedure is completed using 
the Response Code Op Code and the Request Op Code, along with the appropriate Result Code as 
defined in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.13 Set Targeted Distance Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Targeted Distance Op Code is written to the Fitness Machine Control Point and the Result 
Code is ‘Success’, the Server shall use the value sent as a Parameter as the new targeted distance. 
The response shall be indicated when the Set Targeted Distance Procedure is completed using the 
Response Code Op Code and the Request Op Code, along with the appropriate Result Code as defined 
in Section 4.16.2.22. 
Bluetooth SIG Proprietary 
Page 59 of 78 
Fitness Machine Service  /  Service Specification 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.14 Set Targeted Training Time Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Targeted Training Time Op Code is written to the Fitness Machine Control Point and the 
Result Code is ‘Success’, the Server shall use the value sent as a Parameter as the new targeted training 
time. 
The response shall be indicated when the Set Targeted Training Time Procedure is completed using the 
Response Code Op Code and the Request Op Code, along with the appropriate Result Code as defined 
in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.15 Set Targeted Time in Two Heart Rate Zones Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Targeted Training Time in Two Heart Rate Zones Op Code is written to the Fitness 
Machine Control Point and the Result Code is ‘Success’, the Server shall use the values sent as a 
Parameter as the new targeted time in each heart rate zone. The format of the Targeted Time Array 
Parameter is described below: 
LSO 
Targeted Time in Fat Burn Zone 
MSO 
Byte Order LSO...MSO 
Targeted Time in Fitness Zone 
LSO...MSO 
Data type 
UINT16 
UINT16 
Size 
2 octet 
2 octets 
Units 
Second 
Second 
Table 4.17: Targeted Time Array Parameter Format for Set Targeted Training Time in Two Heart Rate Zones 
Procedure 
The response shall be indicated when the Set Targeted Time in Two Heart Rate Zones Procedure is 
completed using the Response Code Op Code and the Request Op Code, along with the appropriate 
Result Code as defined in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
Bluetooth SIG Proprietary 
Page 60 of 78 
Fitness Machine Service  /  Service Specification 
4.16.2.16 Set Targeted Time in Three Zone Heart Rate Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Targeted Training Time in Three Heart Rate Zones Op Code is written to the Fitness 
Machine Control Point and the Result Code is ‘Success’, the Server shall use the values sent as a 
Parameter as the new targeted time in each heart rate zone. The format of the Targeted Time Array 
Parameter is described below: 
LSO 
Targeted Time in Light 
Zone 
MSO 
Targeted Time in Hard 
Zone 
Byte Order LSO...MSO 
Targeted Time in Moderate 
Zone 
LSO...MSO 
Data type 
LSO...MSO 
UINT16 
UINT16 
Size 
UINT16 
2 octet 
2 octets 
Units 
Second 
Second 
2 octets 
Table 4.18: Targeted Time Array Parameter Format for Set Targeted Training Time in Three Heart Rate Zones 
Procedure 
Second 
The response shall be indicated when the Set Targeted Time in Three Heart Rate Zones Procedure is 
completed using the Response Code Op Code and the Request Op Code, along with the appropriate 
Result Code as defined in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.17 Set Targeted Time in Five Zone Heart Rate Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Targeted Training Time in Five Heart Rate Zones Op Code is written to the Fitness 
Machine Control Point and the Result Code is ‘Success’, the Server shall use the values sent as a 
Parameter as the new targeted time in each heart rate zone. The format of the Targeted Time Array 
Parameter is described below: 
LSO 
Targeted Time in 
Very Light Zone 
Targeted Time in 
Light Zone 
Targeted Time in 
Moderate Zone 
MSO 
Targeted Time in 
Hard Zone 
Targeted Time 
in Maximum 
Zone 
Byte Order LSO...MSO 
LSO...MSO 
LSO...MSO 
Data type 
LSO...MSO 
UINT16 
UINT16 
UINT16 
UINT16 
LSO...MSO 
Size 
UINT16 
2 octet 
2 octets 
2 octets 
2 octets 
Units 
2 octets 
Second 
Second 
Second 
Bluetooth SIG Proprietary 
Second 
Second 
Page 61 of 78 
Fitness Machine Service  /  Service Specification 
Table 4.19: Targeted Time Array Parameter Format for Set Targeted Training Time in Five Heart Rate Zones 
Procedure 
The response shall be indicated when the Set Targeted Time in Five Heart Rate Zones Procedure is 
completed using the Response Code Op Code and the Request Op Code, along with the appropriate 
Result Code as defined in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.18 Set Indoor Bike Simulation Parameters Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Indoor Bike Simulation Parameter Op Code is written to the Fitness Machine Control Point 
and the Result Code is ‘Success’, the Server shall use the parameters values sent as a Parameter as the 
new simulation parameters. The format of the Simulation Parameter Array is described below: 
LSO 
Wind Speed 
MSO 
Grade 
Cw (Wind Resistance 
Coefficient) 
Crr (Coefficient of 
Rolling Resistance) 
Byte Order LSO...MSO 
LSO...MSO 
LSO...MSO 
Data type 
LSO...MSO 
SINT16 
SINT16 
UINT8 
Size 
UINT8 
2 octet 
2 octets 
1 octets 
Units 
1 octets 
Meters Per Second (mps) 
Percentage 
Unitless 
Kilogram per Meter 
(Kg/m) 
Resolution 
0.001 
0.01 
0.0001 
Table 4.20: Simulation Parameter Array Format for Set Indoor Bike Simulation Parameters Procedure 
0.01 
The response shall be indicated when the Set Indoor Bike Simulation Mode Procedure is completed using 
the Response Code Op Code and the Request Op Code, along with the appropriate Result Code as 
defined in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.19 Set Wheel Circumference Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Wheel Circumference Op Code is written to the Fitness Machine Control Point and the 
Result Code is ‘Success’, the Server shall use the parameter value sent as a Parameter as the new 
wheel circumference. 
Bluetooth SIG Proprietary 
Page 62 of 78 
Fitness Machine Service  /  Service Specification 
The response shall be indicated when the Set Indoor Bike Simulation Mode Procedure is completed using 
the Response Code Op Code  and the Request Op Code, along with the appropriate Result Code as 
defined in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.20 Spin Down Control Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Spin Down Control Op Code is written to the Fitness Machine Control Point and the Result 
Code is ‘Success’, the Server shall use the value sent as a Parameter to initiate the appropriate spin 
down control. The format of the Control Parameter is UINT8 and the values are described below: 
Control Parameter Value 
Definition 
0x00 
Reserved for Future Use 
0x01 
Start 
0x02 
Ignore 
0x03 – 0xFF 
Table 4.21: Control Parameter Definition for Spin Down Control Procedure 
Reserved for Future Use 
Refer to Appendix 3 for examples related to the Spin Down Procedure. 
The response shall be indicated when the Spin Down Control Procedure is completed using the 
Response Code Op Code and the Request Op Code, along with the appropriate Result Code as defined 
in Section 4.16.2.22. 
If the operation results in a success condition, the Response Parameter shall include a data structure that 
includes the Target Speed Low and the Target Speed High fields as defined in Table 4.22. 
LSO 
Target Speed Low 
Target Speed High 
MSO 
Byte Order LSO...MSO 
LSO...MSO 
Data type 
UINT16 
UINT16 
Size 
2 octet 
2 octets 
Units 
km/h with a resolution of 0.01 km/h 
Table 4.22: Response Parameter when the Spin Down Procedure succeeds 
km/h with a resolution of 0.01 km/h 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
Refer to Appendix 3 for additional information related to this procedure. 
Bluetooth SIG Proprietary 
Page 63 of 78 
Fitness Machine Service  /  Service Specification 
4.16.2.21 Set Targeted Cadence Procedure 
This procedure requires control permission in order to be executed. Refer to Section 4.16.2.1 for more 
information on the Request Control procedure. 
When the Set Targeted Cadence Op Code is written to the Fitness Machine Control Point and the Result 
Code is ‘Success’, the Server shall use the value sent as a Parameter as the new targeted cadence. 
The response shall be indicated when the Set Targeted Distance Procedure is completed using the 
Response Code Op Code and the Request Op Code, along with the appropriate Result Code as defined 
in Section 4.16.2.22. 
If the operation results in an error condition where the Fitness Machine Control Point cannot be indicated 
(e.g., the Client Characteristic Configuration descriptor is not configured for indication or if a procedure is 
already in progress), see Section 4.16.3 for details on handling this condition. 
4.16.2.22 Procedure Complete 
When any of the procedures described in Sections 4.16.2.2 to 4.16.2.17 have been executed by the 
Server or if the procedure generated an error as defined below in this section, the Server shall indicate 
the Fitness Machine Control Point characteristic to the Client. The format of the indication is defined in 
Table 4.23. 
LSO 
Response 
Code Op Code 
(0x80) 
MSO 
Parameter Value 
Request Op Code 
Result Code 
Response Parameter 
(if present) 
Byte Order N/A 
N/A 
N/A 
Data type 
LSO…MSO 
UINT8 
UINT8 
UINT8 
Size 
See Table 4.24 
1 octet 
1 octet 
1 octet 
Table 4.23: Fitness Machine Control Point characteristic – Parameter Value Format of the Response Indication 
0 to 17 octets 
The Response Code field shall be set to 0x80. 
The Request Op Code field shall be set to the value of the Op Code representing the requested 
procedure. 
Table 4.24 defines the Result Code for the Fitness Machine Control Point. 
Result Code 
Definition 
Request Op Code 
Response 
Parameter 
0x00 
Reserved for 
Future Use 
N/A 
0x01 
Success 
N/A 
All Op Codes defined 
in Table 4.15 except 
Spin Down Op Code 
(0x13). 
Bluetooth SIG Proprietary 
None 
Page 64 of 78 
Fitness Machine Service  /  Service Specification 
0x02 
Spin Down Op Code 
(0x13). 
Op Code not 
supported 
See Table 4.22 
All Op Codes defined 
in Table 4.15 as 
reserved for future 
use, or all Op Codes 
that are not supported 
by the Server. 
0x03 
Invalid Parameter 
None 
All Op Codes defined 
in Table 4.15. 
0x04 
Operation Failed 
None 
All Op Codes defined 
in Table 4.15. 
0x05 
Control Not 
Permitted 
None 
All Op Codes defined 
in Table 4.15. 
0x06-0xFF 
Reserved for 
Future Use 
N/A 
None 
N/A 
Table 4.24: Fitness Machine Control Point characteristic – Result Codes 
If an Op Code is written to the Fitness Machine Control Point that results in a successful operation, the 
Server shall indicate the Fitness Machine Control Point with the Response Code Op Code, the Request 
Op Code, and the Result Code set to “Success”. 
If an Op Code is written to the Fitness Machine Control Point and the Server does not permit the control 
to that particular Client, the Server shall respond with the Result Code set to “Control Not Permitted”. 
Depending on the context of the Server, if an Op Code is written to the Fitness Machine Control Point that 
contradicts a previously triggered operation (e.g., the Client sets the targeted speed while targeted 
distance was set or the spin down procedure was ongoing), then previously triggered operation should be 
aborted and the new procedure should be taken into account by the Server. 
If the Start or Resume Op Code is written to the Fitness Machine Control Point that results in an error 
condition (e.g., the fitness machine has already been started), the Server, after sending a Write 
Response, shall indicate the Fitness Machine Control Point with the Response Code Op Code, the 
Request Op Code, and the Result Code set to “Operation Failed”. 
If the Stop or Pause Op Code is written to the Fitness Machine Control Point that results in an error 
condition (e.g., the fitness machine has already been stopped), the Server, after sending a Write 
Response, shall indicate the Fitness Machine Control Point with the Response Code Op Code, the 
Request Op Code, and the Result Code set to “Operation Failed”. 
If an Op Code is written to the Fitness Machine Control Point characteristic that is unsupported by the 
Server (e.g., an Op Code that is Reserved for Future Use), the Server, after sending a Write Response, 
shall indicate the Fitness Machine Control Point with a Response Code Op Code, the Request Op Code, 
and Result Code set to “Op Code Not Supported”. 
If a Parameter is written to the Fitness Machine Control Point characteristic that is invalid (e.g., the Client 
writes the Set Target Speed Op Code with a Parameter that is improperly formatted or that is outside the 
Bluetooth SIG Proprietary 
Page 65 of 78 
Fitness Machine Service  /  Service Specification 
range of the supported values), the Server, after sending a Write Response, shall indicate the Fitness 
Machine Control Point with a Response Code Op Code, the Request Op Code, and Result Code set to 
“Invalid Parameter”. 
If the operation results in an error condition that cannot be reported to the Client using the Fitness 
Machine Control Point (e.g., the Fitness Machine Control Point cannot be indicated), see Section 4.16.3 
for details on handling this condition. 
4.16.3 General Error Handling Procedures 
Other than error handling procedures that are specific to certain Op Codes, the following apply: 
If an Op Code is written to the Fitness Machine Control Point characteristic while the Server is performing 
a previously triggered Fitness Machine Control Point operation (i.e., resulting from invalid Client 
behavior), the Server shall return an error response with the Attribute Protocol error code set to 
“Procedure Already In Progress” as defined in CSS Part B, Section 1.2 [3]. See Appendix 2 for an 
example on how the Server handles this situation. 
If an Op Code is written to the Fitness Machine Control Point characteristic and the Client Characteristic 
Configuration descriptor of the Fitness Machine Control Point is not configured for indications, the Server 
shall return an error response with the Attribute Protocol error code set to “Client Characteristic 
Configuration Descriptor Improperly Configured” as defined in CSS Part B, Section 1.2 [3]. 
4.16.4 Procedure Timeout 
In the context of the Fitness Machine Control Point characteristic, a procedure is started when a write to 
the Fitness Machine Control Point characteristic is successfully completed (i.e., the Server sends a Write 
Response). When a procedure is complete, the Server shall indicate the Fitness Machine Control Point 
with the Op Code set to “Response Code”. 
In the context of the Fitness Machine Control Point characteristic, a procedure is not considered started 
and not queued in the Server when a write to the Fitness Machine Control Point results in an error 
response with an Attribute Protocol error code.