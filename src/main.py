from extraction.extraccion import ejecutar_extraccion
from staging.transformacion_staging import ejecutar_transformacion_staging
from staging.validacion_staging import ejecutar_validacion_staging
from load.carga_dw import ejecutar_proceso


def main():

    ejecutar_extraccion()

    ejecutar_transformacion_staging()

    ejecutar_validacion_staging()

    ejecutar_proceso()


if __name__ == "__main__":
    main()
