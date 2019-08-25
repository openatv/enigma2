#include <stdio.h>
#include <strings.h>
#include <memory.h>
#include <malloc.h>
#include <lib/base/huffman.h>
#include <lib/base/eerror.h>

#define HUFFMAN_MAX_SIZE 4096

type_huffman_node huffman_root;

bool huffman_read_dictionary (char *file)
{
	FILE *fd;
	char line[512];
	char value[256];
	char code[256];
	type_huffman_node *node;
	int length;
	int count = 0;
	int i;

	huffman_root.value = NULL;
	huffman_root.p0 = NULL;
	huffman_root.p1 = NULL;

	eDebug("[huffman] read.. '%s'", file);

	fd = fopen (file, "r");
	if (!fd)
	{
		//eDebug("[huffman] Cannot open dictionary file");
		return false;
	}

	while (fgets (line, sizeof(line), fd))
	{
		memset (value, 0, sizeof (value));
		memset (code, 0, sizeof (code));

		if (sscanf (line, "%c=%[^\n]\n", value, code) != 2)
		{
			if (sscanf (line, "%[^=]=%[^\n]\n", value, code) != 2)
			{
				if (sscanf (line, "=%[^\n]\n", code) != 1)
				{
					continue;
				}
				else
				{
					memset (value, 0, sizeof (value));
				}
			}
		}

		node = &huffman_root;
		length = strlen (code);

		for (i = 0; i < length; i++)
		{
			switch (code[i])
			{
				case '0':
					if (node->p0 == NULL)
					{
						node->p0 = (type_huffman_node*)malloc (sizeof (type_huffman_node));
						node = node->p0;
						node->value = NULL;
						node->p0 = NULL;
						node->p1 = NULL;
						if (length == (i + 1))
						{
							node->value = (char*)malloc (sizeof (char) * (strlen (value) + 1));
							sprintf (node->value, "%s", value);
							count++;
						}
					}
					else
					{
						node = node->p0;
						if ((node->value != NULL) || (length == (i + 1)))
							eDebug("[huffman] Error. Huffman prefix code '%s' already exist", code);
					}
					break;
				case '1':
					if (node->p1 == NULL)
					{
						node->p1 = (type_huffman_node*)malloc (sizeof (type_huffman_node));
						node = node->p1;
						node->value = NULL;
						node->p0 = NULL;
						node->p1 = NULL;
						if (length == (i + 1))
						{
							node->value = (char*)malloc (sizeof (char) * (strlen (value) + 1));
							sprintf (node->value, "%s", value);
							count++;
						}
					}
					else
					{
						node = node->p1;
						if ((node->value != NULL) || (length == (i + 1)))
							eDebug("[huffman] Error. Huffman prefix code '%s' already exist", code);
					}
					break;
			}
		}
	}

	fclose (fd);
	eDebug("[huffman] read.. dictionary completed, read %d values", count);

	return true;
}

void huffman_free_dictionary ()
{
	huffman_free_node (&huffman_root);
}

void huffman_free_node (type_huffman_node *node)
{
	if (node->p0 != NULL)
	{
		huffman_free_node (node->p0);
		free (node->p0);
	}

	if (node->p1 != NULL)
	{
		huffman_free_node (node->p1);
		free (node->p1);
	}

	if (node->value != NULL) free (node->value);
}

bool huffman_decode (const unsigned char *data, int length, char *result, int result_max_length, bool huffman_debug)
{
	type_huffman_node *node = &huffman_root;
	unsigned char byte;
	unsigned char mask;
	int index = 0;
	bool too_long = false;
	int i;
	bool ended = false;

	if (result_max_length > HUFFMAN_MAX_SIZE) result_max_length = HUFFMAN_MAX_SIZE;

	for (i = 0; i < length; i++)
	{
		byte = data[i];
		if (i == 0) mask = 0x20;
		else mask = 0x80;

		do
		{
			if ((byte & mask) == 0)
			{
				if (huffman_debug) printf ("0");
				if (!ended)
				{
					if (node->p0 != NULL) node = node->p0;
					else
					{
						if (!huffman_debug)
						{
							eDebug("[huffman] Error. Cannot decode Huffman data");
							return false;
						}
						printf ("|ERROR|");
						ended = true;
					}
				}
			}
			else
			{
				if (huffman_debug) printf ("1");
				if (!ended)
				{
					if (node->p1 != NULL) node = node->p1;
					else
					{
						if (!huffman_debug)
						{
							eDebug("[huffman] Error. Cannot decode Huffman data");
							return false;
						}
						printf ("|ERROR|");
						ended = true;
					}
				}
			}

			if (node->value != NULL && !ended)
			{
				int size;

				if (huffman_debug) printf ("|%s|", node->value);

				if ((int)(index + strlen(node->value)) >= (result_max_length - 1))
				{
					size = result_max_length - length - 1;
					too_long = true;
				}
				else size = strlen(node->value);

				memcpy (result + index, node->value, size);
				index += size;
				node = &huffman_root;
			}

			if (too_long) break;

			mask = mask >> 1;
		}
		while (mask > 0);

		if (too_long)
		{
			eDebug("[huffman] Warning. Huffman string is too long. Truncated");
			break;
		}
	}

	result[index] = '\0';

	if (!ended)
	{
		if (huffman_debug) printf ("|OK\n%s\n", result);
		return true;
	}
	else
	{
		if (huffman_debug) printf ("\n%s\n", result);
		return false;
	}
}
