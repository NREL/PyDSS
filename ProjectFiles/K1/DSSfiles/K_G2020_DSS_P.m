clear all;

load ('K1L_P.mat');


%load ('K1L_SCADA_P_Sep14to17.mat');


DSS_K_XFORMER1152_L = readtable('/Users/jgiralde/HECO-CRADA/Models/K1-Static/K1_Mon_bb_51066669_l.csv');
DSS_K_XFORMER1435_L = readtable('/Users/jgiralde/HECO-CRADA/Models/K1-Static/K1_Mon_oh_64067_l.csv');
%DSS_K_XFORMER1435_P = readtable('/Users/jgiralde/HECO-CRADA/Models/K1-Static/K1_Mon_oh_64067_pv.csv');

% DSS_Psource = readtable('/Users/jgiralde/HECO-CRADA/Models/Luawai Timeseries/Luawai_Mon_Psourcebus.csv');
% DSS_P = table2array(DSS_Psource(:,3)) + table2array(DSS_Psource(:,5)) + table2array(DSS_Psource(:,7));

for i = 1:size(L1152)
        
    if strcmp(datestr(L1152(i,1)), '29-Jun-2015 00:00:00')
        idx=i
    end
end
%idx=find(L1401(:,1)== datenum('14-Sep-2015 00:00:00'));

% figure (1); plot(L1153(idx:idx+384,1),DSS_P,'-r');hold on; 
% plot(L1153(idx:idx+384,1), SCADA_P);datetick('x','mm/dd/yy','keepticks','keeplimits');
% legend('P DSS Sub', 'P SCADA Sub')

figure(2);subplot(2,1,1);plot(L1152(idx:idx+384,1),L1152(idx:idx+384,2));
datetick('x','mm/dd/yy','keepticks','keeplimits');
hold on;
plot(L1152(idx:idx+384,1),table2array(DSS_K_XFORMER1152_L(1:385,3)),'-r');
%hold on; 
%plot(M31400(idx:idx+384,1),table2array(DSS_M3_XFORMER1400_PV(1:385,3)),'-c');
legend( 'P G2020 KXFORMER1152', 'L DSS KXFORMER1152');


figure(3);subplot(2,1,1);plot(L1152(idx:idx+384,1),L1152(idx:idx+384,2));
datetick('x','mm/dd/yy','keepticks','keeplimits');
hold on;
plot(L1152(idx:idx+384,1),table2array(DSS_K_XFORMER1435_L(1:385,3)),'-r');
%hold on; 
%plot(L1153(idx:idx+384,1),table2array(DSS_M3_XFORMER1413_PV(1:385,3)),'-c');
legend( 'P G2020 KXFORMER1435', 'P DSS LXFORMER1435');



clear all;
load ('K1.mat');

DSS_K_XFORMER1152 = readtable('/Users/jgiralde/HECO-CRADA/Models/K1-Static/K1_Mon_bb_51066669.csv');
DSS_K_XFORMER1435 = readtable('/Users/jgiralde/HECO-CRADA/Models/K1-Static/K1_Mon_oh_64067.csv');
DSS_K_XFORMER1151= readtable('/Users/jgiralde/HECO-CRADA/Models/K1-Static/K1_Mon_oh_50145.csv');

%idx=find(L1153(:,1)== datenum('14-Sep-2015 00:00:00'));
for i = 1:size(L1152)
        
    if strcmp(datestr(L1152(i,1)), '29-Jun-2015 00:00:00')
        idx=i
    end
end

figure(2);subplot(2,1,2);plot(L1152(idx:idx+384,1),L1152(idx:idx+384,2)/240);
datetick('x','mm/dd/yy','keepticks','keeplimits');ylim([0.95,1.05]);
hold on;
plot(L1152(idx:idx+384,1),table2array(DSS_K_XFORMER1152(1:385,3))/2401.8,'-r');
legend( 'V G2020 KXFORMER1152', 'V DSS KXFORMER1152');

figure(3);subplot(2,1,2);plot(L1152(idx:idx+384,1),L1152(idx:idx+384,2)/240);
datetick('x','mm/dd/yy','keepticks','keeplimits');ylim([0.95,1.05]);
hold on;
plot(L1152(idx:idx+384,1),table2array(DSS_K_XFORMER1435(1:385,3))/2401.8,'-r');
legend( 'V G2020 KXFORMER1435', 'V DSS KXFORMER1435');

figure(4);plot(L1152(idx:idx+384,1),L1152(idx:idx+384,2)/240);
datetick('x','mm/dd/yy','keepticks','keeplimits');%ylim([0.95,1.05]);
hold on;
plot(L1152(idx:idx+384,1),table2array(DSS_K_XFORMER1151(1:385,3))/2401.8,'-r');
legend( 'V G2020 KXFORMER1151', 'V DSS KXFORMER1151');


