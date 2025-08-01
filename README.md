# SilentScreenShoter (3S)
Программа для создания и редактирования скриншотов с расширенными функциями. Основные возможности:

**Захват экрана:**
- Полноэкранный режим с возможностью выделения области.
- Горячие клавиши для активации (комбинация левой, правой и средней кнопок мыши).
- ~~Поддержка многомониторных систем.~~

**Редактирование:**
- Инструменты аннотации: стрелки, линии, прямоугольники, рукописные заметки, текст, нумерация.
- Настройка цветов (палитра из 9 цветов + пипетка).
- Размытие выделенных областей.
- Линейка с измерением расстояний и площадей.
- Распознавание контента:
  - OCR (распознавание текста через Tesseract).
  - Декодирование QR-кодов. 
  - Редактирование результатов в отдельном редакторе.

**Экспорт:**
- Копирование в буфер обмена.
- Сохранение в PNG.
- Редактирование распознанного текста во встроенном редакторе.

**Дополнительные функции:**
- Интеграция с поиском Яндекса.
- Поддержка измерения цветов в HEX/RGB/HSL/HSV/CMYK/RAL*.

**Интерфейс:**
- Адаптивная панель инструментов с подсказками.
- Прецизионные инструменты (Alt для детальной информации).

**Программа использует:**
- **Tkinter** для GUI
- **PIL/Pillow** для работы с изображениями
- **pytesseract** для OCR
- **pyzbar** для QR-кодов
- **pynput** для глобальных хоткеев
- **shapely** для геометрических расчетов

Программа ориентирована на быстрый захват и обработку информации с экрана с минимальным вмешательством в рабочий процесс.

***

## Функции программы
**Сделать скриншот** - одновременное нажатие двух кнопок мыши.  
> *Одновременное нажатие **трех** кнопок мыши выводит диалог, с помощью которого можно остановить отслеживание нажатий мыши. Для возобновления отслеживания нужно снова вызвать диалог нажатием трех кнопок и включить программу.*

После запуска программы экран становится затемнённым, и пользователь может с помощью мыши выбрать область для создания скриншота. Если в этом режиме нажать правую кнопку мыши, вызов программы отменится и появится диалог отключения отслеживания. Полезно, если одновременное нажатие двух кнопок мыши уже обрабатывается текущей программой, и его нужно временно заблокировать для 3S.

## Редактор области скриншота

**Меню редактора** - Набор кнопок с основными функциями. Меню "плавающее", его можно переместить в любое место экрана мышкой. При задержке указателя мыши над окном меню редактора появятся подсказки по горячим клавишам.

Все изменения скриншота выполняются в активном окне редактора. Если элементы редактора (линии, стрелки, надписи, и т.п.) не помещаются в окно редактора, то оно автоматически увеличивается.

Изменять размер окна редактора можно в любое время при редактировании с помощью "ручек" на границе окна.

### Возможности редактора скриншотов:

**`Стрелка`** \<F1>  
Рисует стрелку заданным цветом. Во время рисования стрелки можно модифицировать ее вид, вращая колесо мыши. Возможны следующие модификации: стрелка вперед, стрелка назад, стрелка в обе стороны.

**`Карандаш`** \<F2>  
Рисование карандашом произвольных форм заданным цветом. Колесо мышки во время рисования изменяет толщину линии. Замкнутые линии могут быть распознаны и заменены на аналогичные ровные фигуры. Распознаются прямые линии, треугольники, квадраты (прямоугольники), окружности (эллипсы). Для распознавания необходимо чертить фигуру с зажатой клавишей \<Ctrl>.

**`Линия`** \<F3>  
Рисование прямых линий. Начертание линии можно изменить, вращая колесо мышки во время рисования. Возможны следующие виды начертаний: сплошная, пунктир, точки, одинарный штрих-пунктир, двойной штрих-пунктир. Нажатие клавиши \<Shift> во время рисования позволяет рисовать прямые линии под фиксированным углом.

**`Рамка`** \<F4>  
Рисование прямоугольной рамки вокруг объектов на скриншоте. Во время рисования рамки можно колесом мышки модифицировать рамку, изменяя радиусы скругления ее углов.

**`Надпись`** \<F5>  
Создание текста на изображении. Надписи делаются на полупрозрачной подложке и выполняются в два этапа. Первый этап - установка размеров подложки. Второй этап - написание текста. Если текст не входит в размер подложки, то подложка автоматически увеличивается под размер текста. При стирании текста размер подложки возвращается к первоначально заданному размеру. Таким образом, подложка может быть больше чем текст, но не меньше заданного на первом этапе размера. Первый этап можно пропустить, и начать ввод текст сразу после указания точи вставки. Тогда размер подложки не будет контролироваться, и она будет формироваться автоматически в зависимости от объема текста.
Прозрачность подложки можно регулировать при задании ее размера, вращая колесо мыши.
Размер текста регулируется при вводе с помощью клавиш (при зажатом \<Ctrl>) \<+>, \<->, либо колесом мыши при зажатом \<Ctrl>.
Во время ввода текста его положение (вместе с рамкой) можно корректировать стрелками на клавиатуре. Нажатие стрелок при зажатой клавише \<Ctrl> сдвигает текст на больший шаг.
Окончание ввода текста - нажатие клавиши \<Esc>, сочетания \<Ctrl+Enter>, либо переключение на другой элемент редактора (в том числе новый блок текста).

**`"номер"`** \<F6>  
Нумерация объектов на скриншоте. Текущий номер пишется на кнопке. Номер автоматически увеличивается при установке метки на скриншоте. Корректировать текущий номер можно вращая колесо над кнопкой. При установке метки можно так же менять номер вращая колесо мышки пока не отпущена ЛКМ. От метки можно протянуть указатель до объекта.

**`Размытие`** \<F7>  
Скрывает область скриншота под размытием. Степень размытия можно регулировать колесом мышки во время определения границ прямоугольного участка размытия.  
**NOTE** *Алгоритм размытия самый простой, поэтому не очень быстрый, резкие колебания кручения колеса мышки приводят к "подвисаниям"*

**`[Палитра]`** \<0..9>  
Выбор цвета рисования элементов редактора. Позволяет выбрать один из 9 стандартных цветов. Перебор цветов осуществляется кручением колеса мышки над палитрой.
Цвета можно назначать с помощью "горячих клавиш" - цифр.  
\<1> - красный;  
\<2> - оранжевый;  
\<3> - желтый;  
\<4> - зеленый;  
\<5> - голубой;  
\<6> - синий;  
\<7> - фиолетовый;  
\<8> - белый;  
\<9> - черный;  
\<0> - цвет пикселя под курсором.  
При выборе цвета "под курсором", цвет отображается в палитре, но не сохраняется в ней. То есть, при смене цвета колесом он больше не будет встречаться в цикличном выборе.

**`Распознать`** \<Ctrl+R>  
Распознавание текста в области скриншота. Распознается текст на русском и английском языке, а так же содержимое QR кодов со скриншота.\
Для работы функции распознавания в системе должен быть установлен модуль Tesseract OCR (<https://github.com/tesseract-ocr/tesseract>).\
После распознавания запускается **редактор Буфера обмена**.

**`Ok`** \<Enter>, \<Ctrl+C>  
Закрывает окно редактора и копирует скриншот в буфер обмена Windows.  
**NOTE** *При нажатии кнопки `правой кнопкой мыши`, редактор закрывается без сохранения скриншота*

**`Сохранить`** \<Ctrl+S>, \<Ctrl+Shift+C>  
Закрывает окно редактора и позволяет сохранить скриншот в файл в формате PNG.  
**NOTE** *Кнопка является вторым состоянием кнопки `Ok`, которое активируется при нажатом \<Shift>.*

**\<Esc>**  
Закрытие окна редактора без сохранения.

**\<Ctrl+Z>**  
Отмена последнего изменения в окне редактора.

**\<Ctrl+P>**  
Отправка окна редактора на принтер. В качестве вывода на печать используется принтер по умолчанию. Изображение масштабируется на весь лист.

**\<Alt>**  
Переход в "прецизионный" режим. В этом режиме возможна тонкая (вплоть до пикселя) настройка окна редактора, точное указание начала рисования элемента, а так же получение информации о цвете пикселя под курсором. При зажатой клавише \<Alt>, над верхним левом углом окна редактора отображается информер с размером окна. Изменение размера окна можно заблокировать нажатием на информер мышкой. Дополнительно отображается код цвета под курсором в окне редактора, а так же увеличенная область 7px × 7px под курсором. Код цвета может быть представлен в 6 цветовых пространствах - HEX, RGB, HSL, HSV, CMYK, RAL. Вращением колеса мышки можно переключаться между отображаемымими цветовыми пространствами. Клик мышкой в этом режиме добавляет (но не сохраняет!) в палитру цветов цвет под курсором. Нажатие \<Ctrl+C> в прецизионном режиме копирует в буфер обмена информацию о цвете пикселя под курсором в текущей цветовой модели. Для цветовых моделей RGB и HSL информация о цвете сохраняется в виде функций CSS.  
**NOTE** *Цвета на экране монитора ЗНАЧИТЕЛЬНО отличаются от печатных оригиналов из-за особенностей цветопередачи. Цвета RAL не имеют соответствий в системе RGB, поэтому при определении ищется ближайший аналог из каталога RAL Classic.*

**`Средняя кнопка мыши (СКМ)`**  
Вызов инструмента "рулетка". Позволяет измерить объект в окне редактора. Для изменения масштаба рулетки необходимо измерить линейный объект на скриншоте с известной длиной, а затем, не отпуская СКМ, ввести цифрами действительный размер объекта. Завершить ввод нажатием \<Enter>. Все измерения будут отмасштабированы в соответствии с эталонным размером на скриншоте.
Рулетка позволяет измерять не только линейные объекты, но и площади. Дополнительные точки на площади задаются ЛКМ. Нажатие ПКМ в режиме рулетки, убирает дополнительные точки. Площадь измеряется в единицах с учетом линейного масштаба.
Для сброса масштабирования необходимо в режиме линейных измерений нажать \<Enter> не вводя никаких значений

**`Правая кнопка мыши`**  
Удаление объекта на который указывает курсор.
  
***

## Окно редактора Буфер обмена

В окне Буфера обмена содержится распознанный текст, который можно отредактировать прежде чем отправить его в Clipboard. Текст в Clipboard отправляется автоматически при закрытии окна, дополнительно его копировать не нужно. Если на скриншоте содержатся дополнительные данные, такие как QR коды, то они тоже распознаются и открываются в отдельных вкладках окна.  
**NOTE** *В Clipboard передается только содержимое открытой вкладки.*

### Функции окна редактора:

Окно редактора распознает ссылки и email-адреса и делает их "активными".

В окне редактора с помощью контекстного меню можно вызвать поиск Яндекса. Ищется либо слово под курсором, либо выделенный фрагмент текста.

В окне редактора можно "обрамлять" выделенный фрагмент текста парами скобок (), [], {}, а так же кавычками. Для русского языка автоматически ставятся кавычки «ёлочки».

В выделенном фрагменте можно удалить все переносы строк комбинацией \<Ctrl+J>.

Нажатие комбинации клавиш \<Shift+F3> циклично изменяет регистр букв выделенного фрагмента в следующем порядке:
- все строчные
- ВСЕ ПРОПИСНЫЕ
- Первые Буквы Каждого Слова Прописные
- Первая буква выделенного фрагмента - прописная

Поиск по тексту комбинацией клавиш \<Ctrl+F>. Если при вызове был выделен фрагмент, то он сразу подставляется в окно поиска. Найденные фрагменты подсвечиваются, ведется подсчет найденных фрагментов. Закрытие окна поиска - повторное нажатие \<Ctrl+F>, либо \<Esc>.

\<Esc> Закрытие окна редактора с сохранением в буфер обмена информации с активной вкладки
***
## Параметры исполняемого файла
*`-s`, `--silent`*  
Запуск программы в неактивном "тихом" режиме. Для активации программы необходимо нажать одновременно три кнопки мыши и включить SilentScreenShoter.
