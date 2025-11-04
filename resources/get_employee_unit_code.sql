WITH JednostkaWiodaca AS (
    -- 1. Sprawdzenie, czy dla pracownika zdefiniowano jednostkę wiodącą i pobranie jej KODU
    SELECT
        jednostki.UnitCode,
        1 AS Priority -- Najwyższy priorytet
    FROM WFElements AS teczka_pracownika
    -- Dołączenie do procesu jednostek organizacyjnych, aby pobrać kod
    JOIN (
        SELECT
            WFD_ID,
            WFD_AttText2 AS UnitCode
        FROM WFElements
        WHERE WFD_DTYPEID = '121' -- ID procesu 'Jednostki organizacyjne'
    ) AS jednostki ON jednostki.WFD_ID = dbo.ClearWFElemID(teczka_pracownika.WFD_AttChoose11)
    WHERE
        teczka_pracownika.WFD_DTYPEID = 46 -- ID procesu 'Teczka Pracownika'
        AND teczka_pracownika.WFD_Signature = #{Numer_teczki_pracownika}# -- Zmienna Webcon: numer teczki
        AND teczka_pracownika.WFD_AttChoose11 IS NOT NULL AND teczka_pracownika.WFD_AttChoose11 <> ''
),
JednostkaZDaty AS (
    -- 2. Jeśli brak jednostki wiodącej, wyszukanie KODU jednostki na podstawie daty przypisania
    SELECT
        Q1.UnitCode,
        2 AS Priority -- Niższy priorytet
    FROM (
        -- Podzapytanie oparte na [SO]_Pracownicy_Jednostki_Przelozeni.sql
        SELECT
            dbo.ClearWFElemID(DET_Att1) as PersonID,
            WFD_AttText2 as UnitCode, -- ZMIANA: Wybór kodu jednostki zamiast nazwy
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
        Q1.PersonID = (SELECT WFD_ID FROM WFElements WHERE WFD_DTYPEID = 46 AND WFD_Signature = #{Numer_teczki_pracownika}#)
        -- Sprawdzenie, czy podana data mieści się w okresie przypisania pracownika do jednostki
        AND CAST(#{Data_dnia_roboczego}# AS date) >= Q1.DateFrom
        AND (Q1.DateTo IS NULL OR CAST(#{Data_dnia_roboczego}# AS date) <= Q1.DateTo)
),
WszystkieJednostki AS (
    -- 3. Połączenie wyników w jeden zbiór
    SELECT UnitCode, Priority FROM JednostkaWiodaca
    UNION ALL
    SELECT UnitCode, Priority FROM JednostkaZDaty
)
-- 4. Wybranie ostatecznego wyniku na podstawie priorytetu
SELECT TOP 1 UnitCode
FROM WszystkieJednostki
ORDER BY Priority ASC; -- Sortowanie rosnące sprawia, że jednostka wiodąca (Priority=1) będzie pierwsza
