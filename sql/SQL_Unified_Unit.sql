SELECT
    D63.WFD_ID,
    D63.WFD_Signature,
    D63.WFD_Guid,
    D63.WFD_AttChoose10 AS 'Zgłaszający SmartPTR',
    dbo.ClearWFElemID(D63.WFD_AttChoose10) AS 'ID z Teczki',
    D63.WFD_AttText6 AS 'JO zgłaszjącego (SmartPTR)',
    D63.WFD_AttChoose12 AS 'JO prowadząca',
    D63.WFD_AttChoose3 AS 'Prowadzący',
    D63.WFD_AttChoose4 AS 'Przypisani',
    D78_T.WFD_AttText1 AS 'Nazwa jednostki',
    DET73_T.DET_Att2 AS 'Data od',
    DET73_T.DET_Att3 AS 'Data do',
    DET73_T.DET_TSInsert AS 'Data utworzenia jednostki'
FROM
    WFElements D63
JOIN
    WFSteps S63 ON D63.WFD_STPID = S63.STP_ID
JOIN
    WorkFlows W63 ON S63.STP_WFID = W63.WF_ID
-- 1. Łączymy z SQL_53 (Teczka)
-- Relacja: ID z Teczki (63) = ID użytkownika w Teczce (53.WFD_AttText16)
LEFT JOIN (
    SELECT 
        D53.WFD_ID, 
        D53.WFD_AttText16 
    FROM WFElements D53
    JOIN WFSteps S53 ON D53.WFD_STPID = S53.STP_ID
    JOIN WorkFlows W53 ON S53.STP_WFID = W53.WF_ID
    WHERE W53.WF_Guid = '535ce703-16c1-4df2-a38d-8f4dc42cac0e'
      AND D53.WFD_IsDeleted = 0
) D53_T ON dbo.ClearWFElemID(D63.WFD_AttChoose10) = D53_T.WFD_AttText16
-- 2. Łączymy z SQL_73 (Lista Pozycji - Struktura)
-- Relacja: WFD_ID (53) = ID Teczki w strukturze (73.DET_Att1)
LEFT JOIN (
    SELECT 
        DET73.DET_WFDID, 
        DET73.DET_Att2,
        DET73.DET_Att3,
        DET73.DET_TSInsert,
        dbo.ClearWFElemID(DET73.DET_Att1) as DET_Att1_ID 
    FROM WFElementDetails DET73
    JOIN WFConfigurations WFCON ON DET73.DET_WFCONID = WFCON.WFCON_ID
    WHERE WFCON.WFCON_Guid = '924e9282-f968-408d-ae7a-492d1ad46144'
      AND DET73.DET_IsDeleted = 0
) DET73_T ON CAST(D53_T.WFD_ID AS VARCHAR) = DET73_T.DET_Att1_ID
-- 3. Łączymy z SQL_78 (Jednostka)
-- Relacja: ID dokumentu z listy (73.DET_WFDID) = WFD_ID jednostki (78.WFD_ID)
LEFT JOIN (
    SELECT 
        D78.WFD_ID, 
        D78.WFD_AttText1 
    FROM WFElements D78
    JOIN WFSteps S78 ON D78.WFD_STPID = S78.STP_ID
    JOIN WorkFlows W78 ON S78.STP_WFID = W78.WF_ID
    WHERE W78.WF_Guid = '2f2358bf-e7b0-4d9a-9931-b7e9db3d70f7'
      AND D78.WFD_IsDeleted = 0
) D78_T ON DET73_T.DET_WFDID = D78_T.WFD_ID
WHERE
    W63.WF_Guid = '9d1b70e8-9161-4287-97d0-67d1e34e9c3e'
    AND D63.WFD_IsDeleted = 0;
