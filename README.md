# SilentScreenShoter (3S)
программа-сервис для снимков экрана.

***

## Функции программы
**Сделать скриншот** - одновременное нажатие двух кнопок мыши.\
*одновременное нажатие трех кнопок мыши выводит окно, с помощью которого можно остановить отслеживание нажатий мыши. Для возобновления отслеживания нужно снова вызвать диалог нажатием трех кнопок и включить программу.*

После запуска программы окно становится затемнённым, и пользователь может выбрать область экрана для создания скриншота с помощью мыши. Если в этом режиме нажать правую кнопку мыши, вызов программы отменится и появится диалог отключения отслеживания. Полезно, если одновременное нажатие двух кнопок мыши уже обрабатывается текущей программой, и его нужно временно заблокировать для 3S.

## Редактор области скриншота

**Меню редактора** - плавающее окно, которое можно перемещать мышью по экрану. При задержке указателя мыши над окном меню редактора появятся подсказки по горячим клавишам.

Все изменения скриншота выполняются в активном окне редактора. Если элементы редактора (линии, стрелки, надписи, и т.п.) не помещаются в окно редактора, то оно автоматически увеличивается.

Изменять размер окна редактора можно в любое время при редактировании с помощью "ручек" на границе окна.

### Возможности редактора скриншотов:
*[Кнопка] <Горячая клавиша>*

**[Стрелка]** \<F1>\
Рисует стрелку заданным цветом. Во время рисования стрелки можно модифицировать ее вид, вращая колесо мыши. Возможны следующие модификации: стрелка вперед, стрелка назад, стрелка в обе стороны.

**[Карандаш]** \<F2>\
Рисование карандашом произвольных форм заданным цветом. Модификатор колеса мыши изменяет толщину линии. Замкнутые линии могут быть распознаны и заменены на аналогичные ровные фигуры. Распознаются прямые линии, треугольники, квадраты (прямоугольники), окружности (эллипсы). Для распознавания необходимо чертить фигуру с зажатой клавишей \<Ctrl>.

**[Линия]** \<F3>\
Рисование прямых линий. Модификация линий с помощью колеса мыши меняет начертание линии. Возможны следующие виды начертаний: сплошная, пунктир, точки, одинарный штрих-пунктир, двойной штрих-пунктир. Нажатие клавиши \<Shift> во время рисования позволяет рисовать прямые линии под фиксированным углом.

**[Рамка]** \<F4>\
Рисование прямоугольной рамки вокруг объектов на скриншоте. Во время рисования рамки можно колесом мышки модифицировать рамку, изменяя радиусы скругления ее углов.

**[Надпись]** \<F5>\
Создание текста на изображении. Надписи делаются на полупрозрачной подложке и выполняются в этапа. Первый этап - установка размеров подложки. Второй этап - написание текста. Если текст не входит в размер подложки, то подложка автоматически увеличивается под размер текста. При стирании текста размер подложки возвращается к первоначально заданному размеру. Таким образом, подложка может быть больше чем текст, но не меньше заданного на первом этапе размера. Первый этап можно пропустить, и начать ввод текст сразу после указания точи вставки. Тогда размер подложки не будет контролироваться, и она будет формироваться автоматически в зависимости от объема текста.
Прозрачность подложки можно регулировать при задании ее размера, вращая колесо мыши.
Размер текста регулируется при вводе с помощью клавиш (при зажатом \<Ctrl>) \<+>, \<->, либо колесом мыши при зажатом \<Ctrl>.
Во время ввода текста его положение (вместе с рамкой) можно корректировать стрелками на клавиатуре. Нажатие стрелок при зажатой клавише \<Ctrl> сдвигает текст на больший шаг.
Окончание ввода текста - нажатие клавиши \<Esc>, либо переключение на другой элемент редактора (в том числе новый блок текста).

**["номер"]** \<F6>\
Нумерация объектов на скриншоте. Текущий номер пишется на кнопке. Номер автоматически увеличивается при установки метки на скриншоте. Корректировать текущий номер можно вращая колесо над кнопкой. При установке метки можно так же менять номер вращая колесо мышки пока не отпущена ЛКМ. От метки можно протянуть указатель до объекта.

**[Размытие]** \<F7>\
Скрывает область скриншота под размытием. Степень размытия можно регулировать правым колесом мышки во время определения границ прямоугольного участка размытия.
**NOTE** *Алгоритм размытия самый простой, поэтому не очень быстрый, резкие колебания кручения колеса мышки приводят к "подвисаниям"*

**Палитра** \<0..9>\
Выбор цвета рисования элементов редактора. Позволяет выбрать один из 9 стандартных цветов. Перебор цветов осуществляется кручением колеса мышки над палитрой.
Цвета можно назначать с помощью "горячих клавиш" - цифр.
[1] - красный;
[2] - оранжевый;
[3] - желтый;
[4] - зеленый;
[5] - голубой;
[6] - синий;
[7] - фиолетовый;
[8] - белый;
[9] - черный;
[0] - цвет пикселя под курсором.
При выборе цвета "под курсором", цвет отображается в палитре, но не сохраняется в ней. То есть, при смене цвета колесом он больше не будет встречаться в цикличном выборе.

**[Распознать]** \<Ctrl+R>\
Распознавание текста в области скриншота. Распознается текст на русском и английском языке, а так же содержимое QR кодов со скриншота.\
Для работы функции распознавания в системе должен быть установлен модуль Tesseract OCR (<https://github.com/tesseract-ocr/tesseract>). Подробнее в разделе Требования к программе.\
После распознавания открывается **окно редактора Буфера обмена**.

**[Ok]** \<Enter, Ctrl+C>\
Закрывает окно редактора и копирует скриншот в буфер обмена Windows.

**[Сохранить]** \<Ctrl+S, Ctrl+Shift+C>\
Закрывает окно редактора и позволяет сохранить скриншот в файл в формате PNG.
**NOTE** *Кнопка является вторым состоянием кнопки [Ok], которое активируется при нажатом \<Shift>.*

**\<Esc>**\
Закрытие окна редактора без сохранения.

**\<Ctrl+Z>**\
Отмена последнего изменения в окне редактора.

**\<Alt>**\
Переход в "прецизионный" режим. В этом режиме возможна тонкая (вплоть до пикселя) настройка окна редактора, точное указание начала, а так же получение информации о цвете пикселя под курсором. При зажатой клавише \<Alt>, в верхнем правом углу окна редактора появляется информер с размером окна, а так же увеличение области 7px × 7px под курсором. Дополнительно отображается HEX-код цвета под курсором. Клик мышкой в этом режиме добавляет (но не сохраняет!) в палитру цветов цвет под курсором. Нажатие \<Ctrl+C> в прецизионном режиме копирует в буфер обмена информацию о цвете пикселя под курсором (HEX, RGB, HSL, HSV).

**{Средняя кнопка мыши (СКМ)}**\
Вызов инструмента "рулетка". Позволяет измерить объект в окне редактора. Для изменения масштаба рулетки необходимо измерить линейный объект на скриншоте с известной длиной, а затем, не отпуская СКМ, ввести цифрами действительный размер объекта. Завершить ввод нажатием <Enter>. Все измерения будут отмасштабированы в соответствии с эталонным размером на скриншоте.
Рулетка позволяет измерять не только линейные объекты, но и площади. Дополнительные точки на площади задаются ЛКМ. Нажатие ПКМ в режиме рулетки, убирает дополнительные точки. Площадь измеряется в единицах с учетом линейного масштаба.
Для сброса масштабирования необходимо в режиме линейных измерений нажать \<Enter> не вводя никаких значений

**{Правая кнопка мыши}**\
Удаление объекта на который указывает курсор.
  
***

## Окно редактора Буфер обмена

В окне Буфера обмена содержится распознанный текст, который можно отредактировать прежде чем отправить его в Clipboard. Текст в Clipboard отправляется автоматически при закрытии окна, дополнительно его копировать не нужно. Если на скриншоте содержатся дополнительные данные, такие как QR коды, то они тоже распознаются и открываются в отдельных вкладках окна.\
**NOTE** *В Clipboard передается только содержимое открытой вкладки.*

### Функции окна редактора:

Окно редактора распознает ссылки, email-адреса и делает их "активными".

В окне редактора с помощью контекстного меню можно вызвать поиск Яндекса. Ищется либо слово под курсором, либо выделенный фрагмент текста.

В окне редактора можно "обрамлять" выделенный фрагмент текста парами скобок (), [], {}, а так же кавычками. Для русского языка автоматически ставятся кавычки «ёлочки».

В выделенном фрагменте можно удалить все переносы строк комбинацией \<Ctrl+J>.

Нажатие комбинации клавиш \<Shift+F3> циклично изменяет регистр букв выделенного фрагмента в следующем порядке:
- все строчные
- ВСЕ ПРОПИСНЫЕ
- Первые Буквы Каждого Слова Прописные
- Первая буква выделенного фрагмента - прописная

Поиск по тексту комбинацией клавиш \<Ctrl+F>. Если при вызове был выделен фрагмент, то он сразу подставляется в окно поиска. Найденные фрагменты подсвечиваются, ведется подсчет найденных фрагментов. Закрытие окна поиска - повторное нажатие \<Ctrl+F>. либо \<Esc>.
***
## Требования к программе
