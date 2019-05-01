import requests 
import lxml.html
import rdflib;
import sys;
import re;


###########################
# Step 1 - Build Ontology #
###########################

#ontology relations
relationPrefix = 'http://example.com/';
presidentOf = rdflib.URIRef(relationPrefix+"presidentOf");
primeMinisterOf = rdflib.URIRef(relationPrefix+"primeMinisterOf");
population = rdflib.URIRef(relationPrefix+"population");
area = rdflib.URIRef(relationPrefix+"area");
government = rdflib.URIRef(relationPrefix+"government");
capitalOf = rdflib.URIRef(relationPrefix+"capitalOf");
birthDate = rdflib.URIRef(relationPrefix+"birthDate");
wikiLink = rdflib.URIRef(relationPrefix+"wikiLink"); #<entity> <wikiLink> <URL>

#returns URIRef of name
def getEntityRef(name):
    name = relationPrefix + name.replace(' ', '_').replace('\n', '').lower();
    return rdflib.URIRef(name);

#returns rdflib.Literal of type string
def StringLiteral(string):
    return rdflib.Literal(string, datatype=rdflib.XSD.string);

#returns rdflib.Literal of type integer
def IntLiteral(integer):
    result = CleanNumericString(integer);
    return rdflib.Literal(result, datatype=rdflib.XSD.integer);

#remove any non-digit characters in string
def CleanNumericString(string):
    return re.sub('[^0-9]', '', string);

#extract dob of a president or a prime minister
def PersonPage(personName, url):
    r = requests.get(url);
    doc = lxml.html.fromstring(r.content);
    infobox = doc.xpath("//table[contains(@class, 'infobox')]");
    if len(infobox)==0: return;
    infobox = infobox[0];

    dob = infobox.xpath('//th[contains(text(), "Born")]/..//span[contains(@class, "bday")]/text()');
    if len(dob)>0:
        personDob = rdflib.Literal(dob[0],datatype=rdflib.XSD.date);
        ontology.add((getEntityRef(personName), birthDate, personDob));
        if debug: print("      {} dob: {}".format(personName, dob[0]));

def CountryPage(countryName, url):
    #url = 'https://en.wikipedia.org/wiki/Russia';
    #url = 'https://en.wikipedia.org/wiki/United_States'
    #countryName='Russia';

    countryName = getEntityRef(countryName);
    r = requests.get(url);
    doc = lxml.html.fromstring(r.content);
    infobox = doc.xpath("//table[contains(@class, 'infobox')]")[0];

    c = infobox.xpath('.//th[contains(text(), "Capital")]/../td/a'); #capital
    if len(c)>0:
        c=c[0];
        countryCapital = c.xpath('.//text()')[0];
        capitalLink = wiki_prefix + c.xpath('./@href')[0];
    else: #no link
        c = infobox.xpath('.//th[contains(text(), "Capital")]/../td/text()')
        if len(c)>0:
            countryCapital = c[0]
            capitalLink='';
        else:
            countryCapital = ''; #no capital in infobox

    c = infobox.xpath('.//th/a[contains(text(), "Government")]/../../td[1]/a/text()'); #government
    if(len(c))==0:
        c = infobox.xpath('.//th[contains(text(), "Government")]/../td[1]/a/text()')
    countryGovernment = ' '.join(c);

    c = infobox.xpath('.//th/a[contains(text(), "Area")]/../../following::tr[1]/td/text()') #area
    if len(c)>0:
        c = c[0];
    else:
        c = infobox.xpath('.//th[contains(text(), "Area")]/../following::tr[1]/td/text()')[0];

    if c.find('km') > 0: #we want the number that is followed by 'km' (also ignoring area in miles)
        match = re.findall('[0-9][0-9,]*', re.findall('[0-9,]*.km', c)[0]);
    else:
        match = re.findall('[0-9,]*', c); #no 'km' in c
    countryArea = match[0];
    
    #country ruler
    countryPresident = '';
    countryPrimeMinister = '';
    c = infobox.xpath('.//th//a[contains(text(), "President")]/../../../td')
    if len(c) > 0:
        d = c[0].xpath('.//a[1]');
        if len(d)>0:
            countryPresident = d[0].xpath('./text()')[0];
            countryPresidentLink = wiki_prefix + d[0].xpath('./@href')[0];
        else:
            d = c[0].xpath('.//text()');
            countryPresident = d[0];
            countryPresidentLink = '';
        
    c = infobox.xpath('.//th//a[contains(text(), "Prime Minister")]/../../../td')
    if len(c) > 0:
        d = c[0].xpath('.//a[1]');
        if len(d)>0:
            countryPrimeMinister = d[0].xpath('./text()')[0];
            countryPrimeMinisterLink = wiki_prefix + d[0].xpath('./@href')[0];
        else:
            d = c[0].xpath('.//text()');
            countryPrimeMinister = d[0];
            countryPrimeMinisterLink = '';

    #population
    c = infobox.xpath('//th/a[contains(text(), "Population")]/../../following::tr[1]/td/text()');
    if len(c)>0:
        countryPopulation = c[0];
    else:
        c = infobox.xpath('//th[contains(text(), "Population")]/../following::tr[1]/td/text()');
        if len(c)>0:
            countryPopulation = c[0];
        else:
            countryPopulation = '';
    
    if debug: print("   capital:{}|area:{}|president:{}|prime minister:{}|population:{}|government:{}".
              format(countryCapital, countryArea, countryPresident, countryPrimeMinister, countryPopulation, countryGovernment));

    #add to graph
    ontology.add((countryName, area, IntLiteral(countryArea)));
    ontology.add((countryName, government, getEntityRef(countryGovernment)));
    if countryCapital!='':
        ontology.add((getEntityRef(countryCapital), capitalOf, countryName));
        ontology.add((getEntityRef(countryCapital), wikiLink, StringLiteral(capitalLink)));
    if countryPresident!='':
        ontology.add((getEntityRef(countryPresident), presidentOf, countryName));
        if countryPresidentLink!='':
            ontology.add((getEntityRef(countryPresident), wikiLink, StringLiteral(countryPresidentLink)));
            PersonPage(countryPresident, countryPresidentLink);
    if countryPrimeMinister!='':
        ontology.add((getEntityRef(countryPrimeMinister), primeMinisterOf, countryName));
        if countryPrimeMinisterLink!='':
            ontology.add((getEntityRef(countryPrimeMinister), wikiLink, StringLiteral(countryPrimeMinisterLink)));
            PersonPage(countryPrimeMinister, countryPrimeMinisterLink);
    if countryPopulation!='':
        ontology.add((countryName, population, IntLiteral(countryPopulation)));

    ontology.serialize(ontologyFileName, format='nt');
    
def CountryList():
    url = 'https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)';
    r = requests.get(url);
    doc = lxml.html.fromstring(r.content);
    countryTable = doc.xpath("//table[2]/tbody/tr")[2:]; #[2:] to remove the header and total tr
    i=1;
    for tr in countryTable:
        countryName = tr.xpath('./td[2]/a/text()')[0];
        countryLink = wiki_prefix + tr.xpath('./td[2]/a/@href')[0];
        #countryPopulation = tr.xpath('./td[6]/text()')[0];
        if debug: print("Country %s - starting CountryPage"%countryName);

        #add to Graph
        #ontology.add((getEntityRef(countryName), population, IntLiteral(countryPopulation)));
        ontology.add((getEntityRef(countryName), wikiLink, StringLiteral(countryLink)));

        #get more details for this country
        CountryPage(countryName, countryLink);

        #if i==5: break;
        i+=1;

        
########################################
# Step 2 - Parse and answare Questions #
########################################

#returns the answer of @query.
#@additionalString - will be printed before the answer. e.g 'President of' + answer
#@answerType - 'number', 'entity' (for people, capitals etc.) or 'date'.
#returns 'error' when there are no results for @query or a string containing the full answer
def AnswerQuestion(query, additionalString, answerType):
    result = ontology.query(query);
    if len(result)==0:
        return 'error';
    for res in result:
        answer = res[0];
        break; #only one answer needed

    if answerType=='entity':
        answer = answer.replace(relationPrefix, '').replace('_', ' ').capitalize();
        return additionalString + answer;
    if answerType=='number':
        return additionalString + "{:,}".format(answer.value); #format answer as number, seperated by commas
    else:
        return answer;

def ParseQustion(question):
    question = question[:-1]; #remove '?'
    tokens = question.lower().split();
    if tokens[0]=='who':
        answerType = 'entity';
        if question.find('president')>0:
            #Who is the president of <country>
            country = getEntityRef(' '.join(tokens[5:]));
            query = """select ?person where{{ ?person <{}> <{}> .}}""".format(presidentOf, country);
            return AnswerQuestion(query, '', answerType);
        if question.find('prime minister')>0:
            #Who is the prime minister of <country>
            country = getEntityRef(' '.join(tokens[6:]));
            query = """select ?person where{{ ?person <{}> <{}> .}}""".format(primeMinisterOf, country);
            return AnswerQuestion(query, '', answerType); 
        else:
            #Who is <entity>
            entity = getEntityRef(' '.join(tokens[2:]));
            query = "select ?country where{{ <{}> <{}> ?country .}}".format(entity,presidentOf);
            result = AnswerQuestion(query, 'President of ', answerType);
            if result=='error':
                #entity is a Prime Minister
                query = "select ?country where{{ <{}> <{}> ?country .}}".format(entity,primeMinisterOf);
                result = AnswerQuestion(query, 'Prime minister of ', answerType);
            return result;
    if tokens[0]=='what':
        country = getEntityRef(' '.join(tokens[5:]));
        answerType='entity'; #either entity or a number
        km = '';
        if tokens[3]=='population':
            #What is the population of <country>
            query = "select ?pop where {{ <{}> <{}> ?pop .}}".format(country, population);
            answerType = 'number';
        if tokens[3]=='area':
            #What is the area of <country>
            query = "select ?area where {{ <{}> <{}> ?area . }}".format(country, area);
            answerType = 'number';
            km = ' km^2';
        if tokens[3]=='government':
            #What is the government of <country>
            query = "select ?gov where {{ <{}> <{}> ?gov .}}".format(country, government);
        if tokens[3]=='capital':
            #What is the capital of <country>
            query = "select ?capital where {{ ?capital <{}> <{}> .}}".format(capitalOf, country);
        return AnswerQuestion(query, '', answerType)+km;
    if tokens[0]=='when':
        if tokens[3]=='president':
            #When was the president of <country> born
            country = getEntityRef(' '.join(tokens[5:-1]));
            query = """select ?dob where {{ ?person <{}> <{}> .
                                            ?person <{}> ?dob .
                                         }}""".format(presidentOf, country, birthDate);
        if tokens[3]=='prime':
            #When was the prime minister of <country> born
            country = getEntityRef(' '.join(tokens[6:-1]));
            query = """select ?dob where {{ ?person <{}> <{}> .
                                            ?person <{}> ?dob .
                                         }}""".format(primeMinisterOf, country, birthDate);
        return AnswerQuestion(query,'','date');
    else:
        return 'unknown question format';

##########################
# Command Line Arguments #
##########################

debug = True;
error = """Usage: python geo_qa.py create onotology.nt or
       python geo_qa.py question""";

ontology = rdflib.Graph();
ontologyFileName='ontology.nt';
wiki_prefix = "https://en.wikipedia.org";

def main():
    ontologyFileName = 'ontology.nt';
    if len(sys.argv) < 2:
        print(error);
        return;

    if sys.argv[1]=='create':
        ontologyFileName = sys.argv[2];
        CountryList();
        return;
    
    if sys.argv[1]=='question':
        while True:
            question = raw_input('ask a question\n');
            if question=='exit':
                break;
            if len(ontology.all_nodes())==0:
                ontology.parse(ontologyFileName, format='nt');
            print(ParseQustion(question));
    else:
        print(error);
        return;
        
if __name__== "__main__":
    main();




