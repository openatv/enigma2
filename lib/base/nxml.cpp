#include <lib/base/nconfig.h>
#include <string.h>

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#ifdef HAVE_TIME_H
#include <time.h>
#endif

#ifdef HAVE_LIBXML2
#include <libxml/tree.h>
#include <libxml/parser.h>
#include <libxml/parserInternals.h>
#else
#define xmlChar char
#endif /* HAVE_LIBXML2 */

#define DE(x)		((struct nc_de_s *) (data+(x)))
#define IDE(x, y)	(DE(((unsigned *) (data+(x)->offset))[(y)]))
#define XML_DE		((const xmlChar *) "dirEntry")
#define XML_NS		((const xmlChar *) "http://hq.alert.sk/projects/nconfig")
#define XML_ROOT	((const xmlChar *) "NConfigExport")

static char *encodeXml(const char *what)
{
	unsigned p = 0, size = 6*strlen(what)+1;
	char *ret = (char *)malloc(size);
	for (; *what; what++) {
		switch (*what) {
		case '"':
			ret[p++] = '&';
			ret[p++] = 'q';
			ret[p++] = 'u';
			ret[p++] = 'o';
			ret[p++] = 't';
			ret[p++] = ';';
			continue;
		case '>':
			ret[p++] = '&';
			ret[p++] = 'q';
			ret[p++] = 't';
			ret[p++] = ';';
			continue;
		case '<':
			ret[p++] = '&';
			ret[p++] = 'l';
			ret[p++] = 't';
			ret[p++] = ';';
			continue;
		case '&':
			ret[p++] = '&';
			ret[p++] = 'a';
			ret[p++] = 'm';
			ret[p++] = 'p';
			ret[p++] = ';';
			continue;
		}
		if (*what >= 0x20 || *what == '\n' || *what == '\r' || *what == '\t')
			ret[p++] = *what;
		else
			p += sprintf(ret+p, "&#%d;", *what);
	}
	ret[p] = '\0';
	return ret;
}

void NConfig::store(nc_de_s *de, FILE *f)
{
	struct nc_de_s *cc;
	for (unsigned i=0; i<de->pages; i++)
		if ((cc = IDE(de, i))->type) {
			char *encname = encodeXml(data+cc->name);
			fprintf(f, "<nc:%s name=\"%s\" type=\"%d\" value=\"", XML_DE, encname, cc->type);
			free(encname);
			switch (cc->type) {
			case NC_DIR:
				fprintf(f, "%u\">\n", cc->pages);
				store(cc, f);
				fprintf(f, "</nc:%s>\n", XML_DE);
				break;
			case NC_STRING:
				fprintf(f, "%s\"/>\n", encname = encodeXml(data+cc->offset));
				free(encname);
				break;
			case NC_INT:
				fprintf(f, "%lld\"/>\n", *((signed long long *) (data+cc->offset)));
				break;
			case NC_UINT:
				fprintf(f, "%llu\"/>\n", *((unsigned long long *) (data+cc->offset)));
				break;
			case NC_DOUBLE:
				fprintf(f, "%La\"/>\n", *((long double *) (data+cc->offset)));
				break;
			case NC_RAW:
				{
					const char *raw = data+cc->offset;
					for (unsigned j=0; j<cc->pages; j++)
						fprintf(f, "%d%d%d", raw[j] / 100, (raw[j] % 100) / 10, raw[j] % 10);
					fprintf(f, "\"/>\n");
				}
			}
		}
}

int NConfig::toXML(const char *filename)
{
	if (fd < 0)
		return NC_ERR_NFILE;

	FILE *f = fopen(filename, "w");
	if (!f)
		return NC_ERR_PERM;
	
	fprintf(f, "%s", "<?xml version=\"1.0\"?>\n");
	fprintf(f, "<nc:%s xmlns:nc=\"%s\" libVersion=\"%s\"", XML_ROOT, XML_NS, VERSION);
#ifdef HAVE_TIME_H
    time_t t = time(NULL);
    char *tim = ctime(&t);
    tim[strlen(tim)-1] = 0;
	fprintf(f, " time=\"%s\"", tim);
#endif /* HAVE_TIME_H */
	fprintf(f, ">\n");
	lockFile(NC_L_RO);

	store(rdir, f);

	unLockFile();
	fprintf(f, "</nc:%s>\n", XML_ROOT);
	fclose(f);
	return NC_ERR_OK;
}

#ifdef HAVE_LIBXML2
static xmlSAXHandler sh;
enum stateEnum {noRoot = 0, inRoot, inDir, inEnt, unknown};

struct ncParseState {
	stateEnum state, pState;
	xmlChar *ns;
	unsigned depth;
	unsigned unDepth;
	unsigned force;
	NConfig *which;
};

static int ncXmlSAXParseFile(xmlSAXHandlerPtr sax, void *user_data, const char *filename)
{
	int ret = 0;
	xmlParserCtxtPtr ctxt = xmlCreateFileParserCtxt(filename);
	if (!ctxt)
		return -1;
	ctxt->sax = sax;
	ctxt->userData = user_data;
	xmlParseDocument(ctxt);
	ret = ctxt->wellFormed ? 0 : -1;
	if (sax)
		ctxt->sax = NULL;
	xmlFreeParserCtxt(ctxt);
	return ret;
}

static xmlEntityPtr ncXmlGetEntity(void *user_data, const CHAR *name)
{
	return xmlGetPredefinedEntity(name);
}

static void ncXmlStartElement(void *user_data, const CHAR *name, const CHAR **attrs)
{
	struct ncParseState *p = (struct ncParseState *)user_data;
#ifdef NC_DEBUG_XML
	fprintf(stderr, "New element %s state=%d %s\n", name, p->state, p->ns);
#endif
	if (p->state == unknown) {
		p->unDepth++;
		return;
	}
	if (p->state == noRoot) {
		while (*attrs) {
			if (!xmlStrncmp(*attrs, (const xmlChar *) "xmlns:", 6)) {
				if (!xmlStrcmp(attrs[1], XML_NS)) {
					p->ns = xmlStrdup((*attrs)+6);
					break;
				}
			}
			attrs += 2;
		}
		char *b = (char *) malloc(xmlStrlen(p->ns)+xmlStrlen(XML_ROOT)+2);
		sprintf(b, "%s:%s", p->ns, XML_ROOT);
		if (xmlStrcmp(name, (xmlChar *)b)) {
#ifdef NC_DEBUG_XML
			fprintf(stderr, "NewElement, entering unknown %s\n", name);
#endif
			p->pState = p->state;
			p->state = unknown;
		} else
			p->state = inRoot;
		free(b);
		return;
	}
	if (p->state == inRoot || p->state == inDir) {
		const xmlChar *value = NULL, *n = NULL;
		int type = 0;
		while (*attrs) {
			if (!xmlStrcmp(*attrs, (const xmlChar *)"value"))
				value = attrs[1];
			if (!xmlStrcmp(*attrs, (const xmlChar *)"name"))
				n = attrs[1];
			if (!xmlStrcmp(*attrs, (const xmlChar *)"type"))
				type = atoi(attrs[1]);
			attrs += 2;
		}
#ifdef NC_DEBUG_XML
		fprintf(stderr, "%s %s %s %d %d\n", name, n, value, type, p->state);
#endif
		char *b = (char *) malloc(xmlStrlen(p->ns)+xmlStrlen(XML_DE)+2);
		sprintf(b, "%s:%s", p->ns, XML_DE);
		if (xmlStrcmp(name, (xmlChar *)b) || !type || !value || !n) {
#ifdef NC_DEBUG_XML
			fprintf(stderr, "NewElement, entering unknown on mismatch\n");
#endif
			p->pState = p->state;
			p->state = unknown;
			free(b);
			return;
		}
		free(b);
		if (p->force)
			p->which->delKey((const char *)n);

		switch (type) {
		case NC_DIR:
			if (p->which->createDir((const char *)n, strtoul((const char *)value, NULL, 0)) != NC_ERR_OK) {
				p->pState = p->state;
				p->state = unknown;
#ifdef NC_DEBUG_XML
				fprintf(stderr, "NewElement, entering unknown on failed mkdir\n");
#endif
				return;
			}
			p->which->chDir((const char *)n);
			break;
		case NC_STRING:
			p->which->setKey((const char *)n, (const char *)value);
			break;
		case NC_INT:
			p->which->setKey((const char *)n, strtoll((const char *)value, NULL, 0));
			break;
		case NC_UINT:
			p->which->setKey((const char *)n, strtoull((const char *)value, NULL, 0));
			break;
		case NC_DOUBLE:
			{
				long double c;
				sscanf((const char *)value, "%La", &c);
				p->which->setKey((const char *)n, c);
			}
			break;
		case NC_RAW:
			{
				unsigned size = xmlStrlen(value) / 3;
				char *dec = NULL;
				if (size) {
					dec = (char *)malloc(size);
					for (unsigned i=0, k=0; i<size; i++, k += 3)
						dec[i] = value[k] * 100 + value[k+1] * 10 + value[k+2];
				}
				p->which->setKey((const char *)n, dec, size);
				free(dec);
			}
		}
		if (type == NC_DIR) {
			p->state = inDir;
			p->depth++;
		} else {
			p->pState = p->state;
			p->state = inEnt;
		}
		return;
	}
}

static void ncXmlEndElement(void *user_data, const CHAR *name)
{
	struct ncParseState *p = (struct ncParseState *)user_data;
#ifdef NC_DEBUG_XML
	fprintf(stderr, "EndElement %s %s %d\n", name, p->ns, p->state);
#endif
	if (p->state == inEnt) {
		p->state = p->pState;
		return;
	}
	if (p->state == unknown) {
		if (p->unDepth)
			p->unDepth--;
		else
			p->state = p->pState;
		return;
	}
	if (p->state == inRoot) {
		p->state = noRoot;
		free(p->ns);
		p->ns = NULL;
		return;
	}
	if (p->state == inDir) {
		p->depth--;
		if (!p->depth)
			p->state = inRoot;
		p->which->chDir("..");
	}
}
#endif /* HAVE_LIBXML2 */

int NConfig::fromXML(const char *filename, int force)
{
	if (fd < 0)
		return NC_ERR_NFILE;
	if (omode != NC_O_RW)
		return NC_ERR_PERM;
#ifndef HAVE_LIBXML2
	return NC_ERR_NOSUPPORT;
#else
	struct ncParseState state = { noRoot, noRoot, NULL, 0, 0, force, this };
	sh.getEntity = ncXmlGetEntity;
	sh.startElement = ncXmlStartElement;
	sh.endElement = ncXmlEndElement;

	lockFile(NC_L_RW);
	cdir = rdir;
	int ret = ncXmlSAXParseFile(&sh, &state, filename);
	cdir = rdir;
	unLockFile();

	return ret < 0 ? NC_ERR_NVAL : NC_ERR_OK;
#endif /* HAVE_LIBXML2 */
}

