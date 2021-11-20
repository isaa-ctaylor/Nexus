import aiohttp
import asyncio
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Union
import re


class Response:
    def __bool__(self):
        return any(
            getattr(self, str(attr)) for attr in dir(self) if not attr.startswith("_")
        )


@dataclass(unsafe_hash=True, frozen=True)
class Website(Response):
    """
    A class that represents a website returned by the scraper
    """

    title: str
    href: str
    description: str


@dataclass(unsafe_hash=True, frozen=True)
class Link(Response):
    text: str
    href: str


@dataclass(unsafe_hash=True, frozen=True)
class Description(Response):
    text: str
    link: Link


@dataclass(unsafe_hash=True, frozen=True)
class DescriptionAttribute(Response):
    key: Link
    value: str


@dataclass(unsafe_hash=True, frozen=True)
class KnowledgePanel(Response):
    title: str
    subtitle: str
    description: Description
    attributes: List[DescriptionAttribute]
    image: str = None


@dataclass(unsafe_hash=True, frozen=True)
class FeaturedSnippet(Response):
    title: str
    description: str
    link: Link


@dataclass(unsafe_hash=True, frozen=True)
class CalculatorResult(Response):
    equation: str
    answer: str


@dataclass(unsafe_hash=True, frozen=True)
class Currency(Response):
    value: str
    currencytype: str


@dataclass(unsafe_hash=True, frozen=True)
class CurrencyResponse(Response):
    currencyinput: Currency
    currencyoutput: Currency

    when: str


@dataclass(unsafe_hash=True, frozen=True)
class Time(Response):
    time: str
    date: str
    where: str


@dataclass(unsafe_hash=True, frozen=True)
class Definition(Response):
    definition: str
    example: str


@dataclass(unsafe_hash=True, frozen=True)
class WordType(Response):
    wordtype: str
    definitions: List[Definition]


@dataclass(unsafe_hash=True, frozen=True)
class DefinitionResponse(Response):
    word: str
    pronunciation: str
    definitions: List[WordType]


@dataclass(unsafe_hash=True, frozen=True)
class WeatherResponse(Response):
    where: str
    when: str
    description: str
    celcius: int
    fahrenheit: int

    asset: str


@dataclass(unsafe_hash=True, frozen=True)
class Phrase(Response):
    lang: str
    text: str
    pronunciation: str


@dataclass(unsafe_hash=True, frozen=True)
class TranslationResponse(Response):
    source: Phrase
    target: Phrase


@dataclass(unsafe_hash=True, frozen=True)
class Unit(Response):
    unit: str
    value: str


@dataclass(unsafe_hash=True, frozen=True)
class ConversionResponse(Response):
    type_: str

    source: Unit
    target: Unit

    formula: str


@dataclass(unsafe_hash=True, frozen=True)
class Stats(Response):
    results: int
    time: float


@dataclass(unsafe_hash=True, frozen=True)
class SearchResults(Response):
    metrics: str

    websites: List[Website]
    knowledge: KnowledgePanel
    snippet: FeaturedSnippet
    calculator: CalculatorResult
    currency: CurrencyResponse
    localtime: Time
    definition: DefinitionResponse
    eventtime: str
    weather: WeatherResponse
    translation: TranslationResponse
    unitconversion: ConversionResponse


class Scraper:
    def __init__(
        self,
        *,
        base_url: str = "https://www.google.com/",
        lang: str = "en",
        safe: bool = True,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
    ):
        self.base_url = base_url
        self.lang = lang
        self.user_agent = user_agent
        self.safe = safe


class Search(Scraper):
    """
    The Google search results scraper
    """

    async def _get_search_html(self, query: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}search",
                params={
                    "q": str(query),
                    "hl": self.lang,
                    "safe": "active" if self.safe else "images",
                },
                headers={"User-Agent": self.user_agent},
            ) as resp:
                return (
                    BeautifulSoup(
                        await resp.text(), "html.parser", multi_valued_attributes=None
                    ),
                    resp,
                )

    async def _get_websites(self, soup: BeautifulSoup) -> list:
        try:
            websites = soup.find_all("div", class_="g")

            results = set()

            for website in websites:
                title = website.find("h3", class_="LC20lb MBeuO DKV0Md").string.strip()

                href = website.find("a")["href"]

                _ = website.find("div", class_="IsZvec")
                description = (
                    _.find(
                        "div", class_="VwiC3b yXK7lf MUxGbd yDYNvb lyLwlc lEBKkf"
                    ).get_text()
                    if _ is not None and _.find("span") is not None
                    else None
                )

                results.add(Website(title, href, description))

            return sorted(list(results), key=lambda x: x.title)
        except Exception as e:
            return e

    async def _get_knowledge_panel(
        self, soup: BeautifulSoup
    ) -> Union[KnowledgePanel, None]:
        try:
            _ = soup.find("div", class_="osrp-blk")

            if _ is None:
                return

            title = _.find(
                "h2", class_="qrShPb kno-ecr-pt PZPZlf mfMhoc"
            )  # Knowledge card title
            title = title.find("span").string if title else None

            subtitle = _.find("div", class_="wwUB2c PZPZlf")  # Knowledge card subtitle
            subtitle = subtitle.find("span").string if subtitle else None

            image = _.find("g-img", class_="ivg-i PZPZlf")  # Knowledge card image
            image = image["data-lpage"] if image else None

            website = _.find("a", class_="B1uW2d ellip PZPZlf")  # Official website
            website = (
                Link(website.find("span", class_="ellip").string, website["href"])
                if website
                else None
            )

            description = _.find(
                "div", class_="kno-rdesc"
            )  # Knowledge card description
            _dt = description.find("span").string if description else None

            _dl = description.find("a")
            _dl = Link(_dl.string, _dl["href"]) if _dl else None

            description = Description(_dt, _dl)

            attributes = []

            for attribute in _.find_all("div", class_="wDYxhc"):
                name = attribute.find("span", class_="w8qArf")
                name = name.find("a", class_="fl") if name else None

                if not name:
                    continue

                name = Link(
                    name.string, self.base_url + name["href"].split("&stick")[0]
                )

                value = attribute.find("span", class_="LrzXr kno-fv wHYlTd z8gr9e")
                value = value.get_text() if value else None

                attributes.append(DescriptionAttribute(name, value))

            if not any([title, subtitle, description, attributes, image]):
                return

            return KnowledgePanel(title, subtitle, description, attributes, image)
        except Exception as e:
            return e

    async def _get_featured_snippet(
        self, soup: BeautifulSoup
    ) -> Union[FeaturedSnippet, None]:
        _ = soup.find("div", class_="ifM9O")

        if not _:
            return

        title = _.find("a", class_="FLP8od")
        title = title.string if title else None

        description = _.find("span", class_="hgKElc")
        description = description.get_text() if description else None

        a = _.find("div", class_="yuRUbf")
        _at = a.find("h3", class_="LC20lb MBeuO DKV0Md") if a else None
        _at = _at.string if _at else None

        _al = a.find("a") if a else None
        _al = _al["href"] if _al else None

        link = Link(_at, _al)

        return FeaturedSnippet(title, description, link)

    async def _get_calculator_result(
        self, soup: BeautifulSoup
    ) -> Union[CalculatorResult, None]:
        ...

    async def _get_currency_conversion(
        self, soup: BeautifulSoup
    ) -> Union[CurrencyResponse, None]:
        ...

    async def _get_local_time(self, soup: BeautifulSoup) -> Union[Time, None]:
        ...

    async def _get_definition(
        self, soup: BeautifulSoup
    ) -> Union[DefinitionResponse, None]:
        ...

    async def _get_event_time(self, soup: BeautifulSoup) -> Union[str, None]:
        ...

    async def _get_weather_result(
        self, soup: BeautifulSoup
    ) -> Union[WeatherResponse, None]:
        ...

    async def _get_translation(
        self, soup: BeautifulSoup
    ) -> Union[TranslationResponse, None]:
        ...

    async def _get_unit_conversion(
        self, soup: BeautifulSoup
    ) -> Union[ConversionResponse, None]:
        ...

    async def search(self, query: str) -> Union[SearchResults, None]:
        soup = (await self._get_search_html(query))[0]

        websites = await self._get_websites(soup)
        knowledge = await self._get_knowledge_panel(soup)
        snippet = await self._get_featured_snippet(soup)
        calculator = await self._get_calculator_result(soup)
        currency = await self._get_currency_conversion(soup)
        localtime = await self._get_local_time(soup)
        definition = await self._get_definition(soup)
        eventtime = await self._get_event_time(soup)
        weather = await self._get_weather_result(soup)
        translation = await self._get_translation(soup)
        unitconversion = await self._get_unit_conversion(soup)

        try:
            stats = soup.find("div", id="result-stats").get_text().strip("\xa0").strip()

            match = re.match(
                r"About (?P<number>[0-9,]+) results \((?P<time>[0-9.]+) seconds\)",
                stats,
                re.I,
            )

            if match is not None:
                stats = Stats(
                    int(match.group("number").replace(",", "")),
                    float(match.group("time")),
                )
            else:
                stats = None
        except:
            stats = None

        if not any(
            [
                websites,
                knowledge,
                snippet,
                calculator,
                currency,
                localtime,
                definition,
                eventtime,
                weather,
                translation,
                unitconversion,
            ]
        ):
            return

        return SearchResults(
            stats,
            websites,
            knowledge,
            snippet,
            calculator,
            currency,
            localtime,
            definition,
            eventtime,
            weather,
            translation,
            unitconversion,
        )
