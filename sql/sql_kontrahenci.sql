SELECT 
    D.WFD_Signature,
    D.WFD_AttText17 AS NazwaKontrahenta,
    D.WFD_AttText3 AS NIP,
    D.WFD_AttChoose3 AS TypKontrahenta,
    D.WFD_AttChoose4 AS Branza,
    D.WFD_AttChoose2 AS ProfilKontrahenta,
    D.WFD_AttChoose12 AS GrupaFirm
FROM 
    dbo.WFElements D
JOIN 
    dbo.WFSteps S ON D.WFD_STPID = S.STP_ID
JOIN 
    dbo.WorkFlows W ON S.STP_WFID = W.WF_ID
WHERE 
    W.WF_Guid = 'aee5a82c-5eed-465a-8cfc-cf41089c5731'
    AND D.WFD_IsDeleted = 0
    -- Dodany filtr:
    -- AND dbo.ClearWFElem(D.WFD_AttChoose12) = 'Twoja Wartość Tekstowa'