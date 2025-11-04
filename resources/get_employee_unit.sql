WITH JednostkaWiodaca AS (
    -- 1. Sprawdzenie, czy dla pracownika zdefiniowano jednostkę wiodącą w jego teczce
    SELECT
        dbo.ClearWFElem(WFD_AttChoose11) AS UnitName,
        1 AS Priority -- Najwyższy priorytet
    FROM
        WFElements
    WHERE
        WFD_DTYPEID = 46 -- ID procesu 'Teczka Pracownika'
        AND WFD_Signature = '#{Numer_teczki_pracownika}#' -- Zmienna Webcon: numer teczki
        AND WFD_AttChoose11 IS NOT NULL AND WFD_AttChoose11 <> ''
),
JednostkaZDaty AS (
    -- 2. Jeśli brak jednostki wiodącej, wyszukanie jednostki na podstawie daty przypisania
    SELECT
        Q1.UnitName,
        2 AS Priority -- Niższy priorytet
    FROM (
        -- Podzapytanie oparte na [SO]_Pracownicy_Jednostki_Przelozeni.sql
        SELECT
            dbo.ClearWFElemID(DET_Att1) as PersonID,
            WFD_AttText1 as UnitName,
            DET_Att2 AS DateFrom,
            DET_Att3 AS DateTo
        FROM WFElements we
        JOIN WFElementDetails wed on we.WFD_ID = wed.DET_WFDID
        JOIN WFConfigurations wfcon on wed.DET_WFCONID = wfcon.WFCON_ID
        -- GUID'y listy pozycji 'Pracownik w jednostce' oraz 'Przełożony w jednostce'
        WHERE wfcon.WFCON_Guid IN ('924e9282-f968-408d-ae7a-492d1ad46144', 'a575d010-c775-4b02-84a4-b5e886a08645')
          AND we.WFD_STPID = 313 -- Krok obiegu, na którym znajdują się aktywne przypisania
    ) AS Q1
    WHERE
        -- Powiązanie z ID pracownika na podstawie numeru teczki
        Q1.PersonID = (SELECT WFD_ID FROM WFElements WHERE WFD_DTYPEID = 46 AND WFD_Signature = '#{Numer_teczki_pracownika}#')
        -- Sprawdzenie, czy podana data mieści się w okresie przypisania pracownika do jednostki
        AND CAST('#{Data_dnia_roboczego}#' AS date) >= Q1.DateFrom
        AND (Q1.DateTo IS NULL OR CAST('#{Data_dnia_roboczego}#' AS date) <= Q1.DateTo)
),
WszystkieJednostki AS (
    -- 3. Połączenie wyników w jeden zbiór
    SELECT UnitName, Priority FROM JednostkaWiodaca
    UNION ALL
    SELECT UnitName, Priority FROM JednostkaZDaty
)
-- 4. Wybranie ostatecznego wyniku na podstawie priorytetu
SELECT TOP 1 UnitName
FROM WszystkieJednostki
ORDER BY Priority ASC; -- Sortowanie rosnące sprawia, że jednostka wiodąca (Priority=1) będzie pierwsza
