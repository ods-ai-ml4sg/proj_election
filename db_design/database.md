**TABLE Election**

    id INT
        PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    name VARCHAR
    level VARCHAR #уровень выборов: федеральные, региональные, муниципальные
    type VARCHAR #Тип выборов: списочные, одномандатные, многомандатные
    mandates INT #Количество разыгрываемых мандатов
    previous_election_id INT #Для многотуровых выборов ссылку на предыдущий тур
        REFERENCES Election ON DELETE CASCADE
    superior_election_id INT #Для одномандатных выборов в ГД, ссылка на общие выборы в ГД
        REFERENCES Election ON DELETE CASCADE 

**TABLE Nominator** 

Субъект выдвижения: партия, общественная организация, самовыдвижение
    
    id INT
        PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    name VARCHAR
    superior_тominator_id INT #Для региональных отделений партии, ссылка на федеральные партии
        REFERENCES Nominator ON DELETE CASCADE 
    type VARCHAR #Партия, общественная организация, самовыдвижение
    

**TABLE Region** 

Субъект федерации

    id INT
        PRIMARY KEY
    name VARCHAR
        NOT NULL

**TABLE District** 

Округ на выборах. Субъект федерации или муниципальный округ, например

    id INT
        PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    name VARCHAR
        NOT NULL
    type VARCHAR #Регион, округ, район или вся Россия
        NOT NULL

**TABLE Commission** 

Комиссии разных уровней
        
    id INT
        PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    name VARCHAR #Имя или номер
        NOT NULL
    type VARCHAR #Участковая, территориальная, муниципальная, окружная, региональная, центральная
        NOT NULL
    address VARCHAR #физический адрес
        NOT NULL
    superior_commission_id INT #вышестоящая комиссия
        REFERENCES Commission ON DELETE CASCADE
    district_id INT #Округ, которому принадлежит комиссия
        REFERENCES District ON DELETE CASCADE
    election_id INT #Выборы под которые была создан этот инстанс комиссии
        NOT NULL REFERENCES Election ON DELETE CASCADE
    region_id INT #Субъект федерации
        NOT NULL REFERENCES Region ON DELETE CASCADE
    longitude VARCHAR #долгота
    lattitude VARCHAR #широта
    #ещё нужен опциональный foreign key для вышестоящей комисии
    
**TABLE Commission_member** 

Член комиссии (человек, не приклеенный к комиссии)
    
    id INT 
        PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    type VARCHAR #Председатель, зам, секретарь
    name VARCHAR NOT NULL

**TABLE Commission_member_instance** 

Членство в комиссии
    
    id INT 
        PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    position VARCHAR #Председатель, зам, секретарь
    сommission_member_id INT
        NOT NULL REFERENCES Commission_member ON DELETE CASCADE
    nominator_id INT
        NOT NULL REFERENCES Nominator ON DELETE CASCADE


**TABLE Candidate** 

Кандидат или партия, а также испорченные бюллетени
    
    id INT 
        PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    type VARCHAR #партия, человек, испорченные
    name VARCHAR NOT NULL
    nominator_id INT
        REFERENCES Nominator ON DELETE CASCADE

**TABLE Candidate_performance** 

Выступление кандидата/партии на одних выборах
    
    id INT 
        PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    candidate_id INT 
        NOT NULL REFERENCES Сommission Region ON DELETE CASCADE
    election_id INT 
        NOT NULL REFERENCES Election ON DELETE CASCADE
    amount INT #набранные голоса

**TABLE Commission_protocol** 

Данные из первой части протокола (без результатов по кандидатам).
Возможно, стоит объединить с таблицей commission

    id INT 
        PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    commission_id INT 
        NOT NULL REFERENCES Сommission Region ON DELETE CASCADE
    amount_of_voters INT #Число избирателей, включенных в список на момент окончания голосования
    ballots_recieved INT #Число бюллетеней, полученных участковой комиссией
    ballots_given_out_early INT #Число бюллетеней, выданных избирателям, проголосовавшим досрочно в участковой комиссии
    ballots_given_out_at_stations INT #Число бюллетеней, выданных избирателям в помещении для голосования в день голосования
    ballots_given_out_outside INT #Число бюллетеней, выданных избирателям вне помещения для голосования в день голосования
    canceled_ballots INT #Число погашенных бюллетеней
    ballots_found_outside INT #Число бюллетеней, содержащихся в переносных ящиках для голосования
    ballots_found_at_station INT #Число бюллетеней, содержащихся в стационарных ящиках для голосования
    #Число недействительных избирательных бюллетеней (это идёт отельным кандидатом)
    valid_ballots INT #Число действительных бюллетеней
    lost_ballots INT #Число утраченных бюллетеней
    appeared_ballots INT #Число избирательных бюллетеней, не учтенных при получении
   
        
**TABLE Result** 

Набранные кандидатом голоса в одной комиссии
_ЦИК вывешивает результаты по комиссиям, и несмотря на то, что сумма по нижестоящим комиссиям должна быть равна результату в текущей комисии, нет уверенности, что это всегда выполняется. Поэтому будем хранить результаты по всем комиссиям_
    
    id INT 
        PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    candidate_performance_id INT 
        NOT NULL REFERENCES Candidate_performance ON DELETE CASCADE
    commission_id INT 
        NOT NULL REFERENCES Сommission Region ON DELETE CASCADE
    amount INT
